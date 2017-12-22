import inspect
import os
import sys
import traceback
import datetime
from collections import OrderedDict
from multiprocessing import Queue, Event

import git
import qdarkstyle
import zmq
from PyQt5.QtCore import QTimer, QObject
from stytra.calibration import CrossCalibrator, CircleCalibrator

from stytra.collectors import DataCollector, HasPyQtGraphParams,\
    GeneralMetadata, FishMetadata

from stytra.dbconn import put_experiment_in_db, Slacker
from stytra.gui.container_windows import SimpleExperimentWindow,\
    CameraExperimentWindow, TailTrackingExperimentWindow
from stytra.hardware.video import CameraControlParameters, VideoWriter
from stytra.gui.stimulus_display import StimulusDisplayWindow

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource
from stytra.stimulation import ProtocolRunner, protocols
# from stytra.metadata import MetadataCamera
from stytra.stimulation.closed_loop import VigourMotionEstimator, \
    LSTMLocationEstimator
from stytra.stimulation.protocols import Protocol
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.processes import CentroidTrackingMethod, FrameDispatcher, \
    MovingFrameDispatcher
from stytra.tracking.tail import trace_tail_angular_sweep, trace_tail_centroid

import deepdish as dd
import datetime


def get_default_args(func):
    """ Find default arguments of functions
    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def get_classes_from_module(input_module, parent_class):
    """ Find all the classes in a module that are children of a parent one.

    :param input_module: module object
    :param parent_class: parent class object
    :return: OrderedDict of classes
    """
    classes = inspect.getmembers(input_module, inspect.isclass)
    return OrderedDict({prot[1].name: prot[1]
                        for prot in classes if issubclass(prot[1],
                                                               parent_class)})


class Experiment(QObject):
    def __init__(self, directory,
                 calibrator=None,
                 app=None,
                 asset_directory='',
                 debug_mode=True,
                 scope_triggered=False,
                 rec_stim_every=None,
                 notifier='slack'):
        """General class for running experiments
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

        # Maybe Experiment class can inherit from HasPyQtParams itself; but for
        # now I just use metadata object to access the global _params later in
        # the code. This entire Metadata() thing may be replaced.
        self.metadata = GeneralMetadata()
        self.fish_metadata = FishMetadata()
        self.dc = DataCollector(folder_path=self.directory)

        self.last_protocol = \
            self.dc.get_last('stimulus_protocol_params')

        self.prot_class_dict = get_classes_from_module(protocols, Protocol)

        if self.last_protocol is not None:
            ProtocolClass = self.prot_class_dict[self.last_protocol]
            self.protocol_runner = ProtocolRunner(experiment=self,
                                                  protocol=ProtocolClass())
        else:
            self.protocol_runner = ProtocolRunner(experiment=self)

        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        # Projector window and experiment control GUI
        self.window_display = StimulusDisplayWindow(self.protocol_runner,
                                                    self.calibrator,
                                                    record_stim_every=rec_stim_every)

        self.scope_triggered = scope_triggered
        # This has to happen  or version will also be reset to last value:
        if not self.debug_mode:
            self.check_if_committed()

        if scope_triggered:
            self.zmq_context = zmq.Context()
            self.zmq_socket = self.zmq_context.socket(zmq.REP)
            self.zmq_socket.bind("tcp://*:5555")

        if notifier == 'slack':
            self.notifier = Slacker()

    def make_window(self):
        self.window_main = SimpleExperimentWindow(self)
        self.window_main.show()

    def initialize_metadata(self):
        self.dc.add_data_source(self.metadata)

    def check_if_committed(self):
        """ Checks if the version of stytra used to run the experiment is committed,
        so that for each experiment it is known what code was used to record it
        """

        # Get program name and version and save to the metadata:
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha

        self.dc.add_data_source(dict(git_hash=git_hash,
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
        self.window_display.show()
        if full_screen:
            try:
                self.window_display.windowHandle().setScreen(self.app.screens()[1])
                self.window_display.showFullScreen()
            except IndexError:
                print('Second screen not available')

    def start_protocol(self):
        if self.scope_triggered and self.window_main.chk_scope.isChecked():
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            self.dc.add_data_source(self.lightsheet_config,
                                    'imaging_lightsheet_config')
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.protocol_runner.duration)

        self.notifier.post_update("Experiment on setup " +
                                  self.metadata.params['setup_name'] +
                                  " started, it will finish in {}s, or at ".format(self.protocol_runner.duration) +
                                  (datetime.datetime.now()+datetime.timedelta(seconds=self.protocol_runner.duration)).strftime("%H:%M:%S")
                                  )
        self.protocol_runner.start()

    def end_protocol(self, save=True):
        """ Function called at protocol end. Reset protocol, save
        metadata and put experiment data in pymongo database.
        """
        self.protocol_runner.end()
        self.dc.add_data_source(self.protocol_runner.log, name='stimulus_log')
        self.dc.add_data_source(self.protocol_runner.t_start, name='general_t_protocol_start')
        self.dc.add_data_source(self.protocol_runner.t_end,
                                name='general_t_protocol_end')
        # self.dc.add_data_source(self.protocol_runner.dynamic_log.get_dataframe(),
        #                         name='stimulus_dynamic_log')
        clean_dict = self.dc.get_clean_dict(paramstree=True)

        if save:
            if not self.debug_mode:  # upload to database
                db_idx = put_experiment_in_db(self.dc.get_clean_dict(paramstree=True,
                                                                     eliminate_df=True))
                self.dc.add_data_source(db_idx, 'general_db_index')

            self.dc.save()  # save metadata

            # Send notification of experiment end:
            if self.notifier is not None:
                self.notifier.post_update("Experiment on setup " +
                                          clean_dict['general']['setup_name'] +
                                          " is finished running the protocol" +
                                          clean_dict['stimulus']['protocol_params']['name']
                                          +" :birthday:")
                self.notifier.post_update("It was :tropical_fish: " +
                                          str(clean_dict['fish']['id']) +
                                          " of the day, session "
                                          + str(clean_dict['general']['session_id']))

            # Save stimulus movie in .h5 file:
            movie = self.window_display.widget_display.get_movie()
            if movie is not None:
                movie_dict = dict(movie=movie[0], movie_times=movie[1])
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dd.io.save(self.directory + '\\' + timestamp +
                           'stim_movie.h5', movie_dict)

        self.protocol_runner.reset()
        if self.notifier is not None:
            self.notifier.post_update("Experiment on setup " +
                                      clean_dict['general']['setup_name'] +
                                      " is finished running the " +
                                      clean_dict['stimulus']['protocol_params']['name']
                                      +" :birthday:")
            self.notifier.post_update("It was :tropical_fish: " +
                                      str(clean_dict['fish']['id']) +
                                      " of the day, session "
                                      + str(clean_dict['general']['session_id']))

    def wrap_up(self, *args, **kwargs):
        if self.protocol_runner is not None:
            self.protocol_runner.timer.stop()
            if self.protocol_runner.protocol is not None:
                self.end_protocol(save=False)
        self.app.closeAllWindows()
        print('done')


class CameraExperiment(Experiment):
    def __init__(self, *args, video_file=None, **kwargs):
        """
        :param video_file: if not using a camera, the video
        file for the test input
        :param kwargs:
        """
        if video_file is None:
            self.camera = XimeaCamera()
        else:
            self.camera = VideoFileSource(video_file)

        self.camera_control_params = CameraControlParameters()

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        super().__init__(*args, **kwargs)

    def make_window(self):
        self.window_main = CameraExperimentWindow(experiment=self)
        self.window_main.show()
        self.go_live()
        self.initialize_metadata()

    def go_live(self):
        self.gui_timer.start(1000 // 60)
        sys.excepthook = self.excepthook
        self.camera.start()


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


class TailTrackingExperiment(CameraExperiment):
    def __init__(self, *args, motion_estimation=None,
                 motion_estimation_parameters=None,
                 **kwargs):
        """ An experiment which contains tail tracking,
        base for any experiment that tracks behaviour or employs
        closed loops

        :param args:
        :param tracking_method: the method used to track the tail
        :param kwargs:
        """

        self.processing_params_queue = Queue()
        self.finished_sig = Event()
        super().__init__(*args, **kwargs)

        self.tracking_method = CentroidTrackingMethod()
        print(self.tracking_method.params.getValues())

        self.frame_dispatcher = FrameDispatcher(in_frame_queue=
                                                self.camera.frame_queue,
                                                finished_signal=
                                                self.camera.kill_signal,
                                                processing_parameter_queue=
                                                self.processing_params_queue,
                                                gui_framerate=20,
                                                print_framerate=False)

        self.fish_metadata.params['embedded'] = True

        self.data_acc_tailpoints = QueueDataAccumulator(
                                          self.frame_dispatcher.output_queue,
                                          header_list=['tail_sum'] +
                                            ['theta_{:02}'.format(i)
                                             for i in range(
                                                self.tracking_method.params['n_segments'])])

        # start the processes and connect the timers
        self.gui_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)
        self.gui_timer.timeout.connect(
            self.send_new_parameters)
        self.tracking_method.params.param('n_segments').sigValueChanged.connect(
            self.change_segment_numb)
        self.start_frame_dispatcher()

        # Reset tail et experiment start:
        self.protocol_runner.sig_protocol_started.connect(
            self.data_acc_tailpoints.reset)

        # if motion_estimation == 'LSTM':
        #     lstm_name = motion_estimation_parameters['model']
        #     del motion_estimation_parameters['model']
        #     self.position_estimator = LSTMLocationEstimator(self.data_acc_tailpoints,
        #                                                     self.asset_folder + '/' +
        #                                                     lstm_name,
        #                                                     **motion_estimation_parameters)

    def change_segment_numb(self):
        print(self.tracking_method.params['n_segments'])
        new_header = ['tail_sum'] + ['theta_{:02}'.format(i) for i in range(
                            self.tracking_method.params['n_segments'])]
        self.data_acc_tailpoints.reset(header_list=new_header)

        # self.gui_timer.timeout.connect(
        #     self.data_acc_tailpoints.update_list)
        #
        # self.window_main.stream_plot.add_stream(
        #     self.data_acc_tailpoints, ['tail_sum'])

    def send_new_parameters(self):
        self.processing_params_queue.put(
             self.tracking_method.get_clean_values())

    def make_window(self):
        self.window_main = TailTrackingExperimentWindow(experiment=self)
        self.window_main.show()

    def start_protocol(self):
        super().start_protocol()
        self.data_acc_tailpoints.reset()

    def end_protocol(self, *args, **kwargs):
        """ Save tail position and dynamic parameters and terminate.
        """
        self.dc.add_data_source(self.data_acc_tailpoints.get_dataframe(),
                                name='behaviour_tail_log')
        # self.dc.add_data_source('behaviour', 'vr',
        #                         self.position_estimator.log.get_dataframe())
        # temporary removal of dynamic log as it is not correct
        # self.dc.add_data_source(self.protocol_runner.dynamic_log.get_dataframe(),
        #                         name='stimulus_log')
        super().end_protocol(*args, **kwargs)
        try:
            self.position_estimator.reset()
            self.position_estimator.log.reset()
        except AttributeError:
            pass

    def set_protocol(self, protocol):
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)

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

    def start_frame_dispatcher(self):
        self.frame_dispatcher.start()



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
        super().__init__(*args, calibrator=CircleCalibrator(), **kwargs)

        self.processing_params_queue = Queue()
        self.signal_start_rec = Event()
        self.finished_signal = Event()
        self.frame_dispatcher = MovingFrameDispatcher(self.camera.frame_queue,
                                                      finished_signal=self.camera.kill_signal,
                                                      signal_start_rec=self.signal_start_rec,
                                                      gui_framerate=30)

        self.frame_recorder = VideoWriter(self.directory+'/out.mp4',
                                          self.frame_dispatcher.output_queue,
                                          self.finished_signal) # TODO proper filename

    def go_live(self):
        super().go_live()
        self.frame_dispatcher.start()
        self.frame_recorder.start()

    def init_ui(self):
        self.setCentralWidget(self.splitter)
        self.splitter.addWidget(self.camera_view)
        self.splitter.addWidget(self.widget_control)