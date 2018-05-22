import datetime
import inspect
import os
import sys
import traceback
from multiprocessing import Queue, Event

import deepdish as dd
import git
import qdarkstyle
import zmq
from PyQt5.QtCore import QTimer, QObject

from stytra.calibration import CrossCalibrator, CircleCalibrator
from stytra.collectors import DataCollector
from stytra.data_log import HasPyQtGraphParams
from stytra.data_log.metadata import GeneralMetadata, FishMetadata

from stytra.dbconn import put_experiment_in_db, Slacker
from stytra.hardware.video import CameraControlParameters, VideoWriter, \
    VideoFileSource, CameraSource


from stytra.gui.container_windows import SimpleExperimentWindow, \
    CameraExperimentWindow, TailTrackingExperimentWindow, \
    EyeTrackingExperimentWindow
# imports for tracking
from stytra.stimulation import ProtocolRunner, protocols
from stytra.stimulation.closed_loop import VigourMotionEstimator, \
    LSTMLocationEstimator
from stytra.stimulation.protocols import Protocol
from stytra.stimulation.stimulus_display import StimulusDisplayWindow
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.interfaces import *
from stytra.tracking.processes import FrameDispatcher, MovingFrameDispatcher
from stytra.tracking.tail import trace_tail_angular_sweep, trace_tail_centroid

from requests.exceptions import ConnectionError


def get_default_args(func):
    """
    Find default arguments of functions
    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class Experiment(QObject):
    """
    General class that runs an experiment.
    """
    def __init__(self, directory,
                 calibrator=None,
                 app=None,
                 asset_directory='',
                 debug_mode=True,
                 scope_triggered=False,
                 shock_stimulus=False,
                 rec_stim_every=None,
                 display_w = None,
                 display_h = None,
                 notifier='slack'):
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

        self.metadata = GeneralMetadata()
        self.fish_metadata = FishMetadata()
        self.dc = DataCollector(folder_path=self.directory)
        self.dc.add_params(self.metadata._params)

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

        if notifier == 'slack':
            self.notifier = Slacker()

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
                db_idx = put_experiment_in_db(self.dc.get_clean_dict(paramstree=True,
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
                                      str(clean_dict['fish']['id']) +
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


class CameraExperiment(Experiment):
    """ General class for Experiment that need to handle a camera.
    It implements a view of frames from the camera in the control GUI, and the
    respective parameters.
    For debugging it can be used with a video read from file with the
    VideoFileSource class.
    """
    def __init__(self, *args, video_file=None,  camera=None,
                 camera_rotation=0, camera_queue_mb=100, **kwargs):
        """
        :param video_file: if not using a camera, the video file
        file for the test input
        :param kwargs:
        """
        if video_file is None:
            self.camera = CameraSource(camera, rotation=camera_rotation,
                                       max_mbytes_queue=camera_queue_mb)
        else:
            self.camera = VideoFileSource(video_file, rotation=camera_rotation,
                                          max_mbytes_queue=camera_queue_mb)

        self.camera_control_params = CameraControlParameters()

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        super().__init__(*args, **kwargs)

    def start_experiment(self):
        self.go_live()
        super().start_experiment()

    def make_window(self):
        self.window_main = CameraExperimentWindow(experiment=self)
        self.window_main.show()
        self.go_live()

    def go_live(self):
        self.gui_timer.start(1000 // 60)
        # sys.excepthook = self.excepthook
        self.camera.start()
        print('started')

    def wrap_up(self, *args, **kwargs):
        super().wrap_up(*args, **kwargs)
        self.camera.kill_signal.set()
        self.camera.terminate()
        print('Camera process terminated')
        self.gui_timer.stop()

    def excepthook(self, exctype, value, tb):
        traceback.print_tb(tb)
        print('{0}: {1}'.format(exctype, value))
        self.camera.kill_signal.set()
        self.camera.terminate()

# TODO refactoring idea!:
# the trackingMethod from the interfaces probably could be the way of
# keeping together features of a tracking function (such as parameters,
# output accumulator headers, GUI required.


class TrackingExperiment(CameraExperiment):
    """
    Abstract class for an experiment which contains tracking,
    base for any experiment that tracks behaviour (being it eyes, tail,
    or anything else).
    The general purpose of the class is handle a frame dispatcher,
    the relative parameters queue and the output queue.

    The frame dispatcher take two input queues:
        - frame queue from the camera;
        - parameters queue from parameter window.

    and it puts data in three queues:
        - subset of frames are dispatched to the GUI, for displaying;
        - all the frames, together with the parameters, are dispatched
          to perform tracking;
        - the result of the tracking function, is dispatched to a data
          accumulator for saving or other purposes (e.g. VR control).
    """

    tracking_methods_list = dict(centroid=CentroidTrackingMethod,
                                 angle_sweep=AnglesTrackingMethod,
                                 eyes=ThresholdEyeTrackingMethod)

    def __init__(self, *args, tracking_method_name=None, **kwargs):
        """
        :param tracking_method: class with the parameters for tracking (instance
                                of TrackingMethod class, defined in the child);
        :param header_list: headers for the data accumulator (list of strings,
                            defined in the child);
        :param data_name:  name of the data in the final experiment log (defined
                           in the child).
        """

        self.processing_params_queue = Queue()
        self.finished_sig = Event()
        super().__init__(*args, **kwargs)

        TrackingMethod = self.tracking_methods_list[tracking_method_name]
        self.tracking_method = TrackingMethod()

        self.data_name = self.tracking_method.data_log_name
        self.frame_dispatcher = FrameDispatcher(in_frame_queue=
                                                self.camera.frame_queue,
                                                finished_signal=
                                                self.camera.kill_signal,
                                                processing_parameter_queue=
                                                self.processing_params_queue,
                                                gui_framerate=20,
                                                print_framerate=False)

        self.fish_metadata.params['embedded'] = True

        self.data_acc = QueueDataAccumulator(self.frame_dispatcher.output_queue,
                                             header_list=self.tracking_method.accumulator_headers)

        # Data accumulator is updated with GUI timer:
        self.gui_timer.timeout.connect(self.data_acc.update_list)
        # New parameters are sent with GUI timer:
        self.gui_timer.timeout.connect(self.send_new_parameters)
        # Tracking is reset at experiment start:
        self.protocol_runner.sig_protocol_started.connect(
            self.data_acc.reset)

        # start frame dispatcher process:
        self.frame_dispatcher.start()

    def send_new_parameters(self):
        """
        Called upon gui timeout, put tracking parameters in the relative
        queue.
        """
        # TODO do we need this linked to GUI timeout? why not value change?
        self.processing_params_queue.put(
             self.tracking_method.get_clean_values())

    def start_protocol(self):
        """
        Reset data accumulator when starting the protocol.
        """
        # TODO camera queue should be emptied to avoid accumulation of frames!!
        # when waiting for the microscope!
        super().start_protocol()
        self.data_acc.reset()

    def end_protocol(self, *args, **kwargs):
        """
        Save tail position and dynamic parameters and terminate.
        """
        self.dc.add_static_data(self.data_acc.get_dataframe(),
                                name=self.data_name)

        super().end_protocol(*args, **kwargs)
        try:
            self.position_estimator.reset()
            self.position_estimator.log.reset()
        except AttributeError:
            pass

    def set_protocol(self, protocol):
        """
        Connect new protocol start to resetting of the data accumulator.
        """
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc.reset)

    def wrap_up(self, *args, **kwargs):
        super().wrap_up(*args, **kwargs)
        self.frame_dispatcher.terminate()
        print('Dispatcher process terminated')

    def excepthook(self, exctype, value, tb):
        traceback.print_tb(tb)
        print('{0}: {1}'.format(exctype, value))
        self.finished_sig.set()
        self.camera.terminate()
        self.frame_dispatcher.terminate()


class TailTrackingExperiment(TrackingExperiment):
    """
    An experiment which contains tail tracking,
    base for experiments that  employs closed loops.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # This probably should happen before starting the camera process??
        self.tracking_method.params.param('n_segments').sigValueChanged.connect(
            self.change_segment_numb)

    # TODO probably could go to the interface, but this would mean linking
    # the data accumulator to the interface as well. Probably makes sense.
    def change_segment_numb(self):
        new_header = ['tail_sum'] + ['theta_{:02}'.format(i) for i in range(
            self.tracking_method.params['n_segments'])]
        self.data_acc.reset(header_list=new_header)

    def make_window(self):
        self.window_main = TailTrackingExperimentWindow(experiment=self)
        self.window_main.show()


class EyeTrackingExperiment(TrackingExperiment):
    def __init__(self, *args, **kwargs):
        """
        An experiment which contains eye tracking.
        """

        super().__init__(*args,
                         **kwargs)

    def make_window(self):
        self.window_main = EyeTrackingExperimentWindow(experiment=self)
        self.window_main.show()


class VRExperiment(TailTrackingExperiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# class SimulatedVRExperiment(Experiment):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         BoutTuple = namedtuple('BoutTuple', ['t', 'dx', 'dy', 'theta'])
#         bouts = [
#             BoutTuple(2, 5, 1, 0),
#             BoutTuple(6, 0, 0, np.pi/4),
#             BoutTuple(7, 10, 1, 0),
#             BoutTuple(10, 0, 0, np.pi/4),
#             BoutTuple(11, 10, 1, 0),
#             BoutTuple(14, 0, 0, np.pi / 4),
#             BoutTuple(15, 10, 1, 0),
#             BoutTuple(18, 0, 0, np.pi / 4),
#             BoutTuple(19, 10, 1, 0)
#         ]
#         self.set_protocol(VRProtocol(experiment=self,
#                                      background_images=['arrow.png'],
#                                      initial_angle=np.pi/2,
#                                      delta_angle=np.pi/4,
#                                      n_velocities=5,
#                                      velocity_duration=4,
#                                      velocity_mean=10,
#                                      velocity_std=0
#                                      ))
#         self.position_estimator = SimulatedLocationEstimator(bouts)
#
#         self.position_plot = StreamingPositionPlot(data_accumulator=self.protocol.dynamic_log,
#                                                    n_points=1000)
#         self.main_layoutiem = QSplitter()
#         self.main_layoutiem.addWidget(self.position_plot)
#         self.main_layoutiem.addWidget(self.widget_control)
#         self.setCentralWidget(self.main_layoutiem)
#
#         self.gui_refresh_timer = QTimer()
#         self.gui_refresh_timer.setSingleShot(False)
#         self.gui_refresh_timer.start()
#         self.gui_refresh_timer.timeout.connect(self.position_plot.update)
#
#     def end_protocol(self, do_not_save=None):
#         self.dc.add_data_source('stimulus', 'dynamic_parameters',
#                                 self.protocol.dynamic_log.get_dataframe())
#         super().end_protocol(do_not_save)
#
#         self.position_estimator.reset()


class MovementRecordingExperiment(CameraExperiment):
    """ Experiment where the fish is recorded while it is moving

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, calibrator=CircleCalibrator(), camera_queue_mb=500, **kwargs)

        self.processing_params_queue = Queue()
        self.signal_start_rec = Event()
        self.finished_signal = Event()

        self.frame_dispatcher = MovingFrameDispatcher(self.camera.frame_queue,
                                                      finished_signal=self.camera.kill_signal,
                                                      signal_start_rec=self.signal_start_rec,
                                                      processing_parameter_queue=self.processing_params_queue,
                                                      gui_framerate=30)

        self.frame_recorder = VideoWriter(self.directory+"/video/",
                                          self.frame_dispatcher.output_queue,
                                          self.finished_signal)  # TODO proper filename

        self.motion_acc = QueueDataAccumulator(self.frame_dispatcher.diagnostic_queue,
                                               header_list=["n_pixels_difference",
                                                            "recording_state",
                                                            "n_images_in_buffer"])

        self.motion_detection_params = MovementDetectionParameters()
        self.gui_timer.timeout.connect(self.send_params)
        self.gui_timer.timeout.connect(
            self.motion_acc.update_list)

    def make_window(self):
        self.window_main = TailTrackingExperimentWindow(experiment=self, tail_tracking=False)
        self.window_main.show()
        self.go_live()

    def go_live(self):
        super().go_live()
        self.frame_dispatcher.start()
        self.frame_recorder.start()

    def send_params(self):
        self.processing_params_queue.put(self.motion_detection_params.get_clean_values())

    def start_protocol(self):
        self.signal_start_rec.set()
        super().start_protocol()

    def wrap_up(self, *args, **kwargs):
        super().wrap_up(*args, **kwargs)
        self.frame_recorder.terminate()

    def end_protocol(self, *args, **kwargs):
        """ Save tail position and dynamic parameters and terminate.
        """
        self.finished_signal.set()
        self.frame_recorder.reset_signal.set()
        super().end_protocol(*args, **kwargs)
