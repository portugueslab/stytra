import datetime
import os

import deepdish as dd
import git
import qdarkstyle
import zmq
from PyQt5.QtCore import QObject
from requests import ConnectionError

from stytra.calibration import CrossCalibrator
from stytra.collectors import DataCollector

from stytra.stimulation import ProtocolRunner, protocols

from stytra.utilities import Database
from stytra.metadata import AnimalMetadata, GeneralMetadata

from stytra.stimulation.stimulus_display import StimulusDisplayWindow

from stytra.gui.container_windows import SimpleExperimentWindow


class Experiment(QObject):
    """
    General class that runs an experiment.
    """
    def __init__(self, directory,
                 metadata_general=None,
                 metadata_animal=None,
                 calibrator=None,
                 app=None,
                 asset_directory='',
                 debug_mode=True,
                 scope_triggered=False,
                 shock_stimulus=False,
                 rec_stim_every=None,
                 database=None,
                 notifier=None,
                 display_w=None,
                 display_h=None):
        """
        :param directory: data for saving options and data
        :param calibrator:
        :param app: app: a QApplication in which to run the experiment
        :param asset_directory: directory with files for stimuli (movies etc.)
        :param scope_triggered:
        :param debug_mode:
        :param notifier:
        """
        super().__init__()

        self.app = app
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.asset_dir = asset_directory
        self.debug_mode = debug_mode
        self.directory = directory
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator

        self.window_main = None
        if database is None:
            self.database = Database()
        else:
            self.database = database

        self.notifier = notifier

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

        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        self.window_display = StimulusDisplayWindow(self.protocol_runner,
                                                    self.calibrator,
                                                    record_stim_every=rec_stim_every)

        self.scope_triggered = scope_triggered
        # This has to happen here or version will also be reset to last value:
        if not self.debug_mode:
            self.check_if_committed()

        if scope_triggered:
            self.zmq_context = zmq.Context()
            self.zmq_socket = self.zmq_context.socket(zmq.REP)
            self.zmq_socket.bind("tcp://*:5555")

        if shock_stimulus:
            try:
                from stytra.hardware.serial import PyboardConnection
            except ImportError:
                print('Serial pyboard connection not installed')

            self.pyb = PyboardConnection(com_port='COM3')

    def start_experiment(self):
        self.make_window()
        self.initialize_metadata()

    def make_window(self):
        """
        Make experiment GUI, defined in children depending on experiments.
        """
        self.window_main = SimpleExperimentWindow(self)
        self.window_main.show()

    def initialize_metadata(self):
        """
        Restore parameters from saved config.h5 file.
        """
        # When restoring here data_log to previous values, there may be
        # multiple (one per parameter), calls of functions connected to
        # a change in the params three state.
        # See comment in DataCollector.restore_from_saved()
        self.dc.restore_from_saved()

    def check_if_committed(self):
        """
        Checks if the version of stytra used to run the experiment is committed,
        so that for each experiment it is known what code was used to run it.
        """

        # Get program name and version and save to the data_log:
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha

        self.dc.add_static_data(dict(git_hash=git_hash,
                                     name=__file__),
                                name='general_program_version')

        compare = 'HEAD'
        if len(repo.git.diff(compare,
                             name_only=True)) > 0:
            print('The following files contain uncommitted changes:')
            print(repo.git.diff(compare, name_only=True))
            raise PermissionError(
                'The project has to be committed before starting!')

    def show_stimulus_screen(self, full_screen=True):
        """
        Open window to display the visual stimulus and make it full-screen
        if necessary.
        """
        self.window_display.show()
        if full_screen:
            try:
                self.window_display.windowHandle().setScreen(self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print('Second screen not available')

    def start_protocol(self):
        """ Start the protocol from the ProtocolRunner. Before that, send a
        a notification and if required communicate with the microscope to
        synchronize and read configuration.
        """
        if self.notifier is not None and not self.debug_mode:
            try:
                self.notifier.post_update("Experiment on setup " +
                                  self.metadata.params['setup_name'] +
                                  " started, it will finish in {}s, or at ".format(
                                      self.protocol_runner.duration) +
                                  (datetime.datetime.now() + datetime.timedelta(
                                      seconds=self.protocol_runner.duration)).strftime(
                                      "%H:%M:%S")
                                  )

            except ConnectionError:
                print('No internet connection, disabled notifications...')

        if self.scope_triggered and self.window_main.chk_scope.isChecked():
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            self.dc.add_static_data(self.lightsheet_config,
                                    'imaging_lightsheet_config')
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.protocol_runner.duration)

        self.protocol_runner.start()

    def end_protocol(self, save=True):
        """ Function called at Protocol end. Reset Protocol, save
        data_log and put experiment data in pymongo database.
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
            if not self.debug_mode:  # upload to database
                db_idx = self.db.add_experiment(self.dc.get_clean_dict(paramstree=True,
                                                                       eliminate_df=True))
                self.dc.add_static_data(db_idx, 'general_db_index')

            self.dc.save()  # save data_log

            # Save stimulus movie in .h5 file if required:
            movie = self.window_display.widget_display.get_movie()
            if movie is not None:
                movie_dict = dict(movie=movie[0], movie_times=movie[1])
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dd.io.save(self.directory + '\\' + timestamp +
                           'stim_movie.h5', movie_dict, compression='blosc')
                # movie files can be large, and blosc is orders of magnitude faster

        self.protocol_runner.reset()

        # Send notification of experiment end:
        if self.notifier is not None and not self.debug_mode:
            try:
                self.notifier.post_update("Experiment on setup " +
                                      clean_dict['general']['setup_name'] +
                                      " is finished running the " +
                                      clean_dict['stimulus']['protocol_params']['name']
                                      +" :birthday:")
                self.notifier.post_update("It was :tropical_fish: " +
                                      str(clean_dict['animal']['id']) +
                                      " of the day, session "
                                      + str(clean_dict['general']['session_id']))
            except ConnectionError:
                pass

    def wrap_up(self, *args, **kwargs):
        """ Clean up things before closing gui. Called by close button.
        """
        if self.protocol_runner is not None:
            self.protocol_runner.timer.stop()
            if self.protocol_runner.protocol is not None:
                self.end_protocol(save=False)
        self.app.closeAllWindows()
        print('done')