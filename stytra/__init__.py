import sys
import traceback
import os
import zmq
import inspect
import qdarkstyle
import git
from collections import OrderedDict

from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from stytra.gui.stimulus_display import StimulusDisplayWindow
from stytra.calibration import CrossCalibrator, CircleCalibrator

from stytra.collectors import DataCollector, HasPyQtGraphParams, Metadata

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource
from stytra.tracking.processes import CentroidTrackingMethod, FrameDispatcher, \
    MovingFrameDispatcher
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.tail import trace_tail_angular_sweep, trace_tail_centroid

from stytra.gui.container_windows import SimpleExperimentWindow, \
    TailTrackingExperimentWindow, CameraExperimentWindow
from multiprocessing import Queue, Event
from stytra.stimulation import ProtocolRunner, protocols
from stytra.gui.camera_display import CameraControlMethod

# from stytra.metadata import MetadataCamera
from stytra.stimulation.closed_loop import VigourMotionEstimator,\
    LSTMLocationEstimator
from stytra.stimulation.protocols import Protocol

# imports for moving detector
from stytra.dbconn import put_experiment_in_db, Slacker


# this part is needed to find default arguments of functions
def get_default_args(func):
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
                 notifier='slack'):
        """General class for running experiments
        :param directory: data for saving options and data
        :param calibrator:
        :param save_csv:
        :param app: app: A QApplication in which to run the experiment
        :param asset_directory:
        :param debug_mode:
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
        self.metadata = Metadata()
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
                                                    self.calibrator)

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

        # Get program name and version for saving:
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha

        # Save to the metadata
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

        self.protocol_runner.start()

    def end_protocol(self, save=True):
        """ Function called at protocol end. Reset protocol, save
        metadata and put experiment data in pymongo database.
        """
        self.protocol_runner.end()
        self.dc.add_data_source(self.protocol_runner.log, name='stimulus_log')
        # self.dc.add_data_source(self.protocol_runner.dynamic_log.get_dataframe(),
        #                         name='stimulus_dynamic_log')
        clean_dict = self.dc.get_clean_dict(paramstree=True)
        if save:  # save metadata
            self.dc.save()
            if not self.debug_mode:  # upload to database
                put_experiment_in_db(clean_dict)
        self.protocol_runner.reset()
        if self.notifier is not None:
            self.notifier.post_update("Experiment on setup " +
                                      clean_dict['general']['setup_name'] +
                                      " is finished :birthday:")
            self.notifier.post_update("It was :tropical_fish: " +
                                      str(clean_dict['fish']['id']) +
                                      "of the day, session "
                                      + str(clean_dict['general']['session_id']))


    def wrap_up(self, *args, **kwargs):
        if self.protocol_runner is not None:
            if self.protocol_runner.protocol is not None:
                self.end_protocol(save=False)
        self.app.closeAllWindows()


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

        self.camera_control_params = CameraControlMethod()

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        super().__init__(*args, **kwargs)
        self.go_live()

    def make_window(self):
        self.window_main = CameraExperimentWindow(experiment=self)
        self.window_main.show()

    def go_live(self):
        self.camera.start()
        self.gui_timer.start(1000 // 60)
        sys.excepthook = self.excepthook

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


class CameraParams(HasPyQtGraphParams):
    def __init__(self):
        """
        A widget to show the camera and display the controls
        :param experiment: experiment to which this belongs
        """

        super().__init__(name='tracking_camera_params')

        standard_params_dict = dict(exposure={'value': 1000.,
                                              'type': 'float',
                                              'limits': (0.1, 50),
                                              'suffix': 'ms',
                                              'tip': 'Exposure (ms)'},
                                    gain={'value': 1.,
                                          'type': 'float',
                                          'limits': (0.1, 3),
                                          'tip': 'Camera amplification gain'})


class TailTrackingExperiment(CameraExperiment):
    def __init__(self, *args,
                 motion_estimation=None, motion_estimation_parameters=None,
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

        # self.metadata.params[('fish_metadata', 'embedded')] = True

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
        self.start_frame_dispatcher()

        # if motion_estimation == 'LSTM':
        #     lstm_name = motion_estimation_parameters['model']
        #     del motion_estimation_parameters['model']
        #     self.position_estimator = LSTMLocationEstimator(self.data_acc_tailpoints,
        #                                                     self.asset_folder + '/' +
        #                                                     lstm_name,
        #                                                     **motion_estimation_parameters)

    def change_segment_numb(self):
        print(self.tracking_method.params['n_segments'])
        self.data_acc_tailpoints = QueueDataAccumulator(
            self.frame_dispatcher.output_queue,
            header_list=['tail_sum'] +
                        ['theta_{:02}'.format(i)
                         for i in range(
                            self.tracking_method.params['n_segments'])])

    def send_new_parameters(self):
        self.processing_params_queue.put(
             self.tracking_method.get_clean_values())

    def make_window(self):
        self.window_main = TailTrackingExperimentWindow(experiment=self)
        self.window_main.show()

    def start_protocol(self):
        self.data_acc_tailpoints.reset()
        super().start_protocol()

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

    # TODO solve this overwriting go_live, right now not possible because
    # super.init is required before instantiating framedispatcher
    def start_frame_dispatcher(self):
        self.frame_dispatcher.start()
    #
    # def initialize_metadata(self):
    #     print(self.tracking_method._params.getValues())
    #     self.dc.add_data_source(self.tracking_method)
    #     # print(self.tracking_method._params.getValues())


class MovementRecordingExperiment(CameraExperiment):
    """ Experiment where the fish is recorded while it is moving

    """
    def __init__(self, *args, **kwargs):
        self.framestart_queue = Queue()
        super().__init__(*args, **kwargs)

        self.frame_dispatcher = MovingFrameDispatcher(self.frame_queue,
                                                      self.gui_frame_queue,
                                                      self.finished_sig,
                                                      output_queue=self.record_queue,
                                                      framestart_queue=self.framestart_queue,
                                                      signal_start_rec=self.start_rec_sig,
                                                      gui_framerate=30)
        self.go_live()

    def init_ui(self):
        self.setCentralWidget(self.splitter)
        self.splitter.addWidget(self.camera_view)
        self.splitter.addWidget(self.widget_control)