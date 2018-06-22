import datetime
import os
import traceback
from queue import Empty

import deepdish as dd
import qdarkstyle
from PyQt5.QtCore import QObject

from stytra.calibration import CrossCalibrator
from stytra.collectors import DataCollector
from stytra.stimulation import ProtocolRunner

from stytra.metadata import AnimalMetadata, GeneralMetadata

from stytra.stimulation.stimulus_display import StimulusDisplayWindow

from stytra.gui.container_windows import SimpleExperimentWindow


class Experiment(QObject):
    """General class that runs an experiment."""
    def __init__(self, directory,
                 metadata_general=None,
                 metadata_animal=None,
                 calibrator=None,
                 app=None,
                 asset_directory='',
                 rec_stim_every=None,
                 display_config=None,
                 protocols=None,
                 trigger=None):
        """
        :param directory: data for saving options and data
        :param calibrator:
        :param app: app: a QApplication in which to run the experiment
        :param asset_directory: directory with files for stimuli (movies etc.)
        """
        super().__init__()

        self.app = app
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        self.protocols = protocols
        self.trigger = trigger

        self.asset_dir = asset_directory
        self.directory = directory
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator

        self.window_main = None
        self.scope_config = None

        # to the constructor we need to pass classes, not instances
        # otherwise there are problems because the metadatas are QObjects
        if metadata_general is None:
            self.metadata = GeneralMetadata()
        else:
            self.metadata = metadata_general()

        if metadata_animal is None:
            self.animal_metadata = AnimalMetadata()
        else:
            self.animal_metadata = metadata_animal()

        self.dc = DataCollector(folder_path=self.directory)
        self.dc.add_param_tree(self.metadata._params)

        # Use the DataCollector object to find the last used protocol, to
        # restore it
        self.last_protocol = \
            self.dc.get_last_value('stimulus_protocol_params')

        self.protocol_runner = ProtocolRunner(experiment=self,
                                              protocol=self.last_protocol)

        # assign signals from protocol_runner to be used externally:
        self.sig_protocol_finished = self.protocol_runner.sig_protocol_finished
        self.sig_protocol_started = self.protocol_runner.sig_protocol_started

        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        if display_config is None:
            self.display_config = dict(full_screen=False)
        else:
            self.display_config = display_config

        self.window_display = StimulusDisplayWindow(self.protocol_runner,
                                                    self.calibrator,
                                                    record_stim_every=rec_stim_every)

        if self.display_config.get("window_size", None) is not None:
            self.window_display.params['size'] = self.display_config["window_size"]
            self.window_display.set_dims()

    def start_experiment(self):
        """Start the experiment creating GUI and initialising metadata.
        :return:

        Parameters
        ----------

        Returns
        -------

        """
        self.make_window()
        self.initialize_metadata()
        self.show_stimulus_screen(self.display_config["full_screen"])
        if self.trigger is not None:
            self.trigger.start()

    def make_window(self):
        """Make experiment GUI, defined in children depending on experiments."""
        self.window_main = SimpleExperimentWindow(self)
        self.window_main.show()

    def initialize_metadata(self):
        """Restore parameters from saved config.h5 file."""
        # When restoring here data_log to previous values, there may be
        # multiple (one per parameter), calls of functions connected to
        # a change in the params three state.
        # See comment in DataCollector.restore_from_saved()
        self.dc.restore_from_saved()

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
        self.window_display.show()
        if full_screen:
            try:
                self.window_display.windowHandle().setScreen(self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print('Second screen not available')

    def start_protocol(self):
        """Start the protocol from the ProtocolRunner. Before that, send a
        a notification and if required communicate with the microscope to
        synchronize and read configuration.

        Parameters
        ----------

        Returns
        -------

        """
        if self.trigger is not None and self.window_main.chk_scope.isChecked():
            while True:
                if self.trigger.start_event.is_set() and \
                   not self.protocol_runner.running:
                    self.protocol_runner.start()
                    try:
                        self.scope_config = \
                            self.trigger.queue_trigger_params.get(timeout=0.001)
                        self.dc.add_static_data(self.scope_config,
                                                'imaging_microscope_config')
                    except Empty:
                        print('No scope configuration received')
                    break
                else:
                    self.app.processEvents()
        else:
            self.protocol_runner.start()

    def end_protocol(self, save=True):
        """Function called at Protocol end. Reset Protocol, save
        data_log and put experiment data in pymongo database.

        Parameters
        ----------
        save :
             (Default value = True)

        Returns
        -------

        """
        self.protocol_runner.stop()
        self.dc.add_static_data(self.protocol_runner.log, name='stimulus_log')
        self.dc.add_static_data(self.protocol_runner.t_start, name='general_t_protocol_start')
        self.dc.add_static_data(self.protocol_runner.t_end,
                                name='general_t_protocol_end')

        # TODO saving of dynamic_log should be conditional
        # self.dc.add_data_source(self.protocol_runner.dynamic_log.get_dataframe(),
        #                         name='stimulus_dynamic_log')
        clean_dict = self.dc.get_clean_dict(paramstree=True)

        if save:
            self.dc.save()  # save data_log
            # Save stimulus movie in .h5 file if required:
            movie = self.window_display.widget_display.get_movie()
            if movie is not None:
                movie_dict = dict(movie=movie[0], movie_times=movie[1])
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dd.io.save(self.directory + '\\' + timestamp +
                           'stim_movie.h5', movie_dict, compression='blosc')
                # movie files can be large, and blosc is orders of magnitude
                # faster

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
            if self.protocol_runner.protocol is not None:
                self.end_protocol(save=False)
        if self.trigger is not None:
            self.trigger.kill_event.set()
            # self.trigger.join()
            self.trigger.terminate()
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
        print('{0}: {1}'.format(exctype, value))
        self.trigger.kill_event.set()
        self.trigger.terminate()
