import datetime
import os
import traceback
from queue import Empty
import numpy as np
import deepdish as dd
import logging
import tempfile
import git
import sys

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QByteArray
from PyQt5.QtWidgets import QMessageBox

from stytra.calibration import CrossCalibrator
from stytra.collectors import DataCollector
from stytra.stimulation import ProtocolRunner
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation.stimulus_display import StimulusDisplayWindow
from stytra.gui.container_windows import (
    SimpleExperimentWindow,
    DynamicStimExperimentWindow,
)

import imageio

try:
    import av
except ImportError:
    pass

from lightparam import Parametrized, Param


class Experiment(QObject):
    """General class that runs an experiment.

    Parameters
    ----------
    app : QApplication()
        Application to run the Experiment QObject.
    protocol : object of :class:`Protocol <stytra.stimulation.Protocol>`
        list of protocols that can be run in this experiment session.
    directory : str
        (optional) Directory where metadata will be saved. If None, nothing
        will be
        saved (default: None).
    metadata_general: :class:`GeneralMetadata <stytra.metadata.GeneralMetadata>` object
        (optional) Class for saving general metadata about the experiment. I
        If not passed, a default GeneralMetadata object will be set.
    metadata_animal: :class:`AnimalMetadata <stytra.metadata.AnimalMetadata>` object
        (optional) Class for saving animal metadata about the experiment.
        If not passed, a default AnimalMetadata object will be set.
    calibrator : :class:`Calibrator <stytra.calibration.Calibrator>` object
        (optional) Calibrator object to calibrate the stimulus display. If
        not set, a CrossCalibrator will be used.
    asset_directory : str
        (optional) Path where asset files such as movies or images to be
        displayed can be found.
    display_config: dict
        (optional) Dictionary with specifications for the display. Possible
        key values are "full_screen" and "window_size".
        gl_display : bool (False)
    rec_stim_framerate : int
        (optional) Set to record a movie of the displayed visual stimulus. It
        specifies every how many frames one will be saved (set to 1 to
        record) all displayed frames. The final movie will be saved in the
        directory in an .h5 file.
    trigger : :class:`Trigger <stytra.triggering.Trigger>` object
        (optional) Trigger class to control the beginning of the stimulation.
    offline : bool
        if stytra is used in offline analysis, stimulus is not displayed
    log_format : str
        one of "csv", "feather", "hdf5" (pytables-based) or "json"
    """

    sig_data_saved = pyqtSignal()

    def __init__(
        self,
        app=None,
        protocol=None,
        dir_save=None,
        dir_assets="",
        database=None,
        metadata_general=None,
        metadata_animal=None,
        calibrator=None,
        stim_plot=False,
        loop_protocol=False,
        log_format="csv",
        stim_movie_format="h5",
        rec_stim_framerate=None,
        display=None,
        scope_triggering=None,
        offline=False,
        **kwargs
    ):
        """ """
        self.arguments = locals()
        super().__init__()

        self.app = app
        self.protocol = protocol
        self.trigger = scope_triggering
        self.offline = offline

        self.asset_dir = dir_assets

        if dir_save is None:
            dir_save = tempfile.gettempdir()
        self.base_dir = dir_save
        self.database = database
        self.use_db = True if database else False
        self.log_format = log_format
        self.stim_movie_format = stim_movie_format
        self.stim_plot = stim_plot
        self.loop_protocol = loop_protocol

        self.dc = DataCollector(folder_path=self.base_dir)

        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator

        self.dc.add(self.calibrator)

        self.window_main = None
        self.scope_config = None
        self.abort = False

        self.logger = logging.getLogger()
        self.logger.setLevel("INFO")

        # We will collect data only of a directory for saving is specified:
        # Conditional, in case metadata are generated and passed from the
        # configuration file:
        if metadata_general is None:
            self.metadata = GeneralMetadata(tree=self.dc)
        else:
            self.metadata = metadata_general(tree=self.dc)

        if metadata_animal is None:
            self.metadata_animal = AnimalMetadata(tree=self.dc)
        else:
            self.metadata_animal = metadata_animal(tree=self.dc)

        self.gui_params = Parametrized(
            "gui", tree=self.dc, params=dict(geometry=Param(""), window_state=Param(""))
        )

        self.protocol_runner = ProtocolRunner(experiment=self)

        # assign signals from protocol_runner to be used externally:
        self.sig_protocol_finished = self.protocol_runner.sig_protocol_finished
        self.sig_protocol_started = self.protocol_runner.sig_protocol_started

        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        if display is None:
            self.display_config = dict(full_screen=False, gl=True)
        else:
            self.display_config = display

        if not self.offline:
            self.window_display = StimulusDisplayWindow(
                self.protocol_runner,
                self.calibrator,
                gl=self.display_config.get("gl", True),
                record_stim_framerate=rec_stim_framerate,
            )

        self.i_run = 0
        self.current_timestamp = datetime.datetime.now()
        self.current_instance = self.get_new_name()

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        self.display_framerate_acc = None

    def save_log(self, log, name, category="tracking"):
        log.save(self.filename_base() + name, self.log_format)
        self.dc.add_static_data(
            self.filename_prefix() + name + "." + self.log_format, category + "/" + name
        )

    def get_new_name(self):
        return (
            self.current_timestamp.strftime("%y%m%d")
            + "_f"
            + str(self.metadata_animal.id)
        )

    @property
    def folder_name(self):
        foldername = os.path.join(
            self.base_dir, self.protocol.__class__.name, self.get_new_name()
        )
        if not os.path.isdir(foldername):
            os.makedirs(foldername)
        return foldername

    def filename_prefix(self):
        return self.current_timestamp.strftime("%H%M%S_")

    def filename_base(self):
        # Save clean json file as timestamped Ymd_HMS_metadata.h5 files:
        return os.path.join(self.folder_name, self.filename_prefix())

    def start_experiment(self):
        """Start the experiment creating GUI and initialising metadata.

        Parameters
        ----------

        Returns
        -------

        """
        self.dc.restore_from_saved()
        self.make_window()

        self.show_stimulus_screen(self.display_config["full_screen"])
        self.window_display.set_dims()

        if self.display_config.get("window_size", None) is not None:
            self.window_display.size = self.display_config["window_size"]
            self.window_display.set_dims()

        if self.trigger is not None:
            print("start")
            self.trigger.start()

    def restore_window_state(self):
        if self.gui_params.window_state:
            self.window_main.restoreState(
                QByteArray.fromHex(bytes(self.gui_params.window_state, "ascii"))
            )
            self.window_main.restoreGeometry(
                QByteArray.fromHex(bytes(self.gui_params.geometry, "ascii"))
            )

    def make_window(self):
        """Make experiment GUI, defined in children depending on experiments.
        """
        if self.stim_plot:
            self.window_main = DynamicStimExperimentWindow(self)
            self.window_main.stream_plot.add_stream(self.protocol_runner.dynamic_log)
            self.gui_timer.start(1000 // 60)
        else:
            self.window_main = SimpleExperimentWindow(self)

        self.window_main.construct_ui()
        self.window_main.show()

    def show_stimulus_screen(self, full_screen=True):
        """Open window to display the visual stimulus and make it full-screen
        if necessary.

        Parameters
        ----------
        full_screen :
             (Default value = True)

        Returns
        -------

        """
        if self.offline:
            return None
        self.window_display.show()
        if full_screen:
            try:
                self.window_display.windowHandle().setScreen(self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print("Second screen not available")

    def start_protocol(self):
        """Start the protocol from the ProtocolRunner. Before that, send a
        a notification and if required communicate with the microscope to
        synchronize and read configuration.

        Parameters
        ----------

        Returns
        -------

        """
        self.abort = False
        self.window_display.widget_display.reset()
        if self.trigger is not None and self.window_main.chk_scope.isChecked():
            self.logger.info("Waiting for trigger signal...")
            msg = QMessageBox()
            msg.setText("Waiting for trigger event...")
            msg.setStandardButtons(QMessageBox.Abort)
            msg.buttonClicked.connect(self.abort_start)
            msg.show()
            while True and not self.abort:
                if (
                    self.trigger.start_event.is_set()
                    and not self.protocol_runner.running
                ):
                    msg.close()
                    self.protocol_runner.start()
                    try:
                        self.scope_config = self.trigger.queue_trigger_params.get(
                            timeout=0.001
                        )
                        self.logger.info(self.scope_config)
                        if self.dc is not None:
                            self.dc.add_static_data(
                                self.scope_config, "imaging/microscope_config"
                            )
                    except Empty:
                        self.logger.info("No trigger configuration received")
                    break
                else:
                    self.app.processEvents()
        else:
            self.protocol_runner.start()

    def abort_start(self):
        self.logger.info("Aborted")
        self.abort = True

    def end_protocol(self, save=True):
        """Function called at Protocol end. Reset Protocol and save
        data_log.

        Parameters
        ----------
        save : bool
             Specify whether to save experiment data (Default value = True).

        Returns
        -------

        """

        self.protocol_runner.stop()
        if self.base_dir is not None and save:
            if self.dc is not None:
                self.dc.add_static_data(self.protocol_runner.log, name="stimulus/log")
                self.dc.add_static_data(
                    self.protocol_runner.t_start, name="general/t_protocol_start"
                )
                self.dc.add_static_data(
                    self.protocol_runner.t_end, name="general/t_protocol_end"
                )

                if self.database is not None and self.use_db:
                    db_id = self.database.insert_experiment_data(
                        self.dc.get_clean_dict(
                            eliminate_df=True, convert_datetime=False
                        )
                    )
                else:
                    db_id = -1
                self.dc.add_static_data(db_id, name="general/db_index")

                # Get program name and version and save to the data_log:
                try:
                    repo = git.Repo(sys.argv[0], search_parent_directories=True)
                    git_hash = repo.head.object.hexsha
                    self.dc.add_static_data(
                        dict(
                            git_hash=git_hash,
                            name=sys.argv[0],
                            arguments=self.arguments,
                        ),
                        name="general/program_version",
                    )
                except git.InvalidGitRepositoryError:
                    self.logger.info("Invalid git repository")

                self.dc.save(self.filename_base() + "metadata.json")  # save data_log
                self.logger.info(
                    "Saved log files under {}".format(self.filename_base())
                )

                # save the stimulus movie if it is generated
                movie, movie_times = self.window_display.widget_display.get_movie()
                if movie is not None:
                    if self.stim_movie_format == "h5":
                        movie_dict = dict(
                            movie=np.stack(movie, 0), movie_times=movie_times
                        )
                        dd.io.save(
                            self.filename_base() + "stim_movie.h5",
                            movie_dict,
                            compression="blosc",
                        )
                    elif self.stim_movie_format == "mp4":
                        imageio.mimwrite(
                            self.filename_base() + "stim_movie.mp4",
                            movie,
                            fps=30,
                            quality=None,
                            ffmpeg_params=[
                                "-pix_fmt",
                                "yuv420p",
                                "-profile:v",
                                "baseline",
                                "-level",
                                "3",
                            ],
                        )
                    else:
                        raise Exception(
                            "Tried to write the stimulus video into an unsupported format"
                        )

            if self.protocol_runner.dynamic_log is not None:
                self.save_log(
                    self.protocol_runner.dynamic_log, "stimulus_log", "stimulus"
                )

        self.i_run += 1
        self.current_timestamp = datetime.datetime.now()

        self.sig_data_saved.emit()

        if self.loop_protocol and self.protocol_runner.completed:
            self.protocol_runner.reset()
            self.start_protocol()
        else:
            self.protocol_runner.reset()

    def wrap_up(self, *args, **kwargs):
        """Clean up things before closing gui. Called by close button.

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        if self.protocol_runner is not None:
            self.protocol_runner.timer.stop()
            if (
                self.protocol_runner.protocol is not None
                and self.protocol_runner.running
            ):
                self.end_protocol(save=False)

        if self.trigger is not None:
            self.trigger.kill_event.set()
            print("killed")
            self.trigger.join()
            print("joined")

        st = self.window_main.saveState()
        geom = self.window_main.saveGeometry()
        self.gui_params.window_state = bytes(st.toHex()).decode("ascii")
        self.gui_params.geometry = bytes(geom.toHex()).decode("ascii")
        self.dc.save_config_file()
        self.app.closeAllWindows()

    def excepthook(self, exctype, value, tb):
        """

        Parameters
        ----------
        exctype :

        value :

        tb :


        Returns
        -------

        """
        traceback.print_tb(tb)
        print("{0}: {1}".format(exctype, value))
        self.trigger.kill_event.set()
        self.trigger.join()
