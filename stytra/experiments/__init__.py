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
import types
import imageio

from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QByteArray
from PyQt5.QtWidgets import QMessageBox

from stytra.calibration import CrossCalibrator
from stytra.collectors import DataCollector
from stytra.stimulation import ProtocolRunner
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation.stimulus_display import StimulusDisplayWindow
from stytra.gui.container_windows import (
    ExperimentWindow,
    VisualExperimentWindow,
    DynamicStimExperimentWindow,
)

import pkg_resources

try:
    import av
except ImportError:
    pass

from lightparam import Parametrized, Param


def imports():
    for name, val in globals().items():
        if isinstance(val, types.ModuleType) and hasattr(val, "__version__"):
            yield val.__name__ + ":" + str(val.__version__)


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
    display: dict
        (optional) Dictionary with specifications for the display. Possible
        key values are
        full_screen: bool (False)
        window_size: Tuple(Int, Int)
        framerate: target framerate, if 0, it is the highest possilbe
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
            instance_number=-1,
            database=None,
            metadata_general=None,
            metadata_animal=None,
            loop_protocol=False,
            log_format="csv",
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
        self.framerate_goals = dict(display=30)

        self.asset_dir = dir_assets

        if dir_save is None:
            dir_save = tempfile.gettempdir()
        self.base_dir = dir_save
        self.database = database
        self.use_db = True if database else False
        self.log_format = log_format
        self.loop_protocol = loop_protocol

        self.dc = DataCollector(folder_path=self.base_dir,
                                instance_number=instance_number)

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

        # This is done to save GUI configuration:
        self.gui_params = Parametrized(
            "gui", tree=self.dc,
            params=dict(geometry=Param(""), window_state=Param(""))
        )

        self.protocol_runner = ProtocolRunner(experiment=self)

        # assign signals from protocol_runner to be used externally:
        self.sig_protocol_finished = self.protocol_runner.sig_protocol_finished
        self.sig_protocol_started = self.protocol_runner.sig_protocol_started

        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        self.i_run = 0
        self.current_timestamp = datetime.datetime.now()

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        self.t0 = datetime.datetime.now()

        self.animal_id = None
        self.session_id = None

    @property
    def folder_name(self):
        foldername = os.path.join(
            self.base_dir, self.protocol.__class__.name, self.animal_id
        )
        if not os.path.isdir(foldername):
            os.makedirs(foldername)
        return foldername

    def filename_prefix(self):
        return self.session_id + "_"

    def filename_base(self):
        # Save clean json file as timestamped Ymd_HMS_metadata.h5 files:
        return os.path.join(self.folder_name, self.filename_prefix())

    def save_log(self, log, name, category="tracking"):
        logname = log.save(self.filename_base() + name, self.log_format)

        self.dc.add_static_data(logname, category + "/" + name)

    def initialize_plots(self):
        pass

    def set_id(self):
        self.animal_id = (
            self.current_timestamp.strftime("%y%m%d") + "_f"
            + str(self.metadata_animal.id)
        )
        self.session_id = self.current_timestamp.strftime("%H%M%S")

    def reset(self):
        self.t0 = datetime.datetime.now()
        if self.protocol_runner.dynamic_log is not None:
            self.protocol_runner.dynamic_log.reset()

        self.protocol_runner.framerate_acc.reset()

    def start_experiment(self):
        """Start the experiment creating GUI and initialising metadata.

        Parameters
        ----------

        Returns
        -------

        """
        self.gui_timer.start(1000 // 60)
        self.dc.restore_from_saved()
        self.set_id()
        self.make_window()
        self.protocol_runner.update_protocol()

        if self.trigger is not None:
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
        self.window_main = ExperimentWindow(self)

        self.window_main.construct_ui()
        self.window_main.show()

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
                    self.reset()
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
            self.reset()
            self.protocol_runner.start()

    def abort_start(self):
        self.logger.info("Aborted")
        self.abort = True

    def save_data(self):
        if self.base_dir is not None:
            if self.dc is not None:
                self.dc.add_static_data(self.protocol_runner.log,
                                        name="stimulus/log")
                self.dc.add_static_data(
                    self.t0, name="general/t_protocol_start"
                )
                self.dc.add_static_data(
                    self.protocol_runner.t_end, name="general/t_protocol_end"
                )
                self.dc.add_static_data(
                    self.animal_id, name="general/fish_id"
                )
                self.dc.add_static_data(
                    self.session_id, name="general/session_id"
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

                # Clean up arguments dict:
                try:
                    kwargs = self.arguments.pop("kwargs")
                    self.arguments.update(kwargs)
                except KeyError:
                    pass

                # Get program name and version and save to the data_log:
                git_hash = None
                version = None

                try:
                    repo = git.Repo(sys.argv[0], search_parent_directories=True)
                    git_hash = repo.head.object.hexsha
                    try:
                        version = pkg_resources.get_distribution(
                            'stytra').version
                    except pkg_resources.DistributionNotFound:
                        self.logger.info("Could not find stytra version")

                except git.InvalidGitRepositoryError:
                    self.logger.info("Invalid git repository")

                self.dc.add_static_data(
                    dict(
                        git_hash=git_hash,
                        name=sys.argv[0],
                        arguments=self.arguments,
                        version=version,
                        dependencies=list(imports())
                    ),
                    name="general/program_version",
                )

                self.dc.save(
                    self.filename_base() + "metadata.json")  # save data_log
                self.logger.info(
                    "Saved log files under {}".format(self.filename_base())
                )

            if self.protocol_runner.dynamic_log is not None:
                self.save_log(
                    self.protocol_runner.dynamic_log, "stimulus_log", "stimulus"
                )

            self.sig_data_saved.emit()

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
        self.set_id()

        if save:
            self.save_data()

        self.i_run += 1
        self.current_timestamp = datetime.datetime.now()

        self.reset()
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
            if (self.protocol_runner.protocol is not None
                and self.protocol_runner.running):
                self.end_protocol(save=False)

        if self.trigger is not None:
            self.trigger.kill_event.set()
            self.trigger.join()

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


class VisualExperiment(Experiment):
    """General class that runs an experiment.

    Parameters
    ----------
    calibrator : :class:`Calibrator <stytra.calibration.Calibrator>` object
        (optional) Calibrator object to calibrate the stimulus display. If
        not set, a CrossCalibrator will be used.
    display_config: dict
        (optional) Dictionary with specifications for the display. Possible
        key values are "full_screen" and "window_size".
        gl_display : bool (False)
    rec_stim_framerate : int
        (optional) Set to record a movie of the displayed visual stimulus. It
        specifies every how many frames one will be saved (set to 1 to
        record) all displayed frames. The final movie will be saved in the
        directory in an .h5 file.
    offline : bool
        if stytra is used in offline analysis, stimulus is not displayed
    """

    sig_data_saved = pyqtSignal()

    def __init__(
        self, *args,
        calibrator=None,
        stim_plot=False,
        stim_movie_format="h5",
        rec_stim_framerate=None,
        display=None,
        **kwargs
    ):
        """ """
        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator
        self.stim_movie_format = stim_movie_format
        self.stim_plot = stim_plot

        super().__init__(*args, **kwargs)
        self.dc.add(self.calibrator)

        if display is None:
            self.display_config = dict(full_screen=False, gl=True)
        else:
            self.display_config = display
            target_fps = self.display_config.get("framerate", 0)
            if target_fps > 0:
                self.protocol_runner.target_dt = 1000//target_fps

        if not self.offline:
            self.window_display = StimulusDisplayWindow(
                self.protocol_runner,
                self.calibrator,
                gl=self.display_config.get("gl", True),
                record_stim_framerate=rec_stim_framerate,
            )

        self.display_framerate_acc = None
        self.protocol_runner.framerate_acc.goal_framerate = self.display_config.get("min_framerate", None)

    def start_experiment(self):
        """Start the experiment creating GUI and initialising metadata.

        Parameters
        ----------

        Returns
        -------

        """
        super().start_experiment()

        if self.display_config.get("window_size", None) is not None:
            self.window_display.size = self.display_config["window_size"]
            self.window_display.set_dims()

        self.show_stimulus_screen(self.display_config.get("full_screen", False))

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
            self.window_main = VisualExperimentWindow(self)

        self.window_main.construct_ui()
        self.window_main.show()

    def start_protocol(self):
        """Start the protocol from the ProtocolRunner. Before that, send a
        a notification and if required communicate with the microscope to
        synchronize and read configuration.

        Parameters
        ----------

        Returns
        -------

        """
        self.window_display.widget_display.reset()
        super().start_protocol()

    def save_data(self):
        if self.base_dir is not None:
            if self.dc is not None:
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
        super().save_data()

    def show_stimulus_screen(self, full_screen=False):
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
                self.window_display.windowHandle().setScreen(
                    self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print("Second screen not available")
