import sys
import traceback
import os
import zmq
import inspect
import qdarkstyle
import git

from PyQt5.QtWidgets import QMainWindow, QCheckBox, QVBoxLayout, QSplitter
from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from stytra.gui.control_gui import ProtocolControlWidget
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.calibration import CrossCalibrator, CircleCalibrator

from stytra.collectors import DataCollector, HasPyQtGraphParams, Metadata

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource, FrameDispatcher
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.tail import tail_trace_ls, detect_tail_embedded
from stytra.gui.camera_display import CameraTailSelection, CameraViewCalib
from stytra.gui.plots import MultiStreamPlot, StreamingPositionPlot
from multiprocessing import Queue, Event
from stytra.stimulation import ProtocolRunner

from stytra.metadata import MetadataCamera
from stytra.stimulation.closed_loop import VigourMotionEstimator,\
    LSTMLocationEstimator

# imports for moving detector
from stytra.hardware.video import MovingFrameDispatcher
from stytra.dbconn import put_experiment_in_db


# this part is needed to find default arguments of functions
def get_default_args(func):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class Experiment(QObject):
    sig_calibrating = pyqtSignal()
    def __init__(self, directory,
                 calibrator=None,
                 save_csv=False,
                 app=None,
                 asset_directory='',
                 debug_mode=True):
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

        self.protocol_runner = ProtocolRunner(experiment=self)
        self.protocol_runner.sig_protocol_finished.connect(self.end_protocol)

        # Maybe Experiment class can inherit from HasPyQtParams itself; but for now I just
        # use metadata object to access the global _params later in the code.
        # This entire Metadata() thing may be replaced by params in the experiment
        self.metadata = Metadata()
        self.dc = DataCollector(folder_path=self.directory)
        self.dc.add_data_source(self.protocol_runner.log, name='stimulus_log')
        self.dc.add_data_source(self.metadata)

        # Projector window and experiment control GUI
        self.window_display = StimulusDisplayWindow()
        self.window_display.widget_display.calibrator = self.calibrator
        self.window_display.widget_display.set_protocol_runner(self.protocol_runner)

        self.widget_control = ProtocolControlWidget(display_window=self.window_display,
                                                    experiment=self)

        self.widget_control.show()

        # This has to happen after or version will be reset together with the rest
        if not self.debug_mode:
            self.check_if_committed()

        self.widget_control.reset_ROI()  # update ROI to set to new loaded size


    def check_if_committed(self):
        """ Checks if the version of stytra used to run the experiment is committed,
        so that for each experiment it is known what code was used to record it
        """

        # Get program name and version for saving:
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha

        # Save to the metadata
        self.metadata.params.addChild({'name': 'version', 'type': 'group',
                                       'value': [{'name': 'git_hash', 'value': git_hash},
                                                 {'name': 'program', 'value': __file__}]})

        if len(repo.git.diff('HEAD~1..HEAD',
                             name_only=True)) > 0:
            print('The following files contain uncommitted changes:')
            print(repo.git.diff('HEAD~1..HEAD', name_only=True))
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
        self.protocol_runner.start()

    def end_protocol(self, do_not_save=None):
        self.protocol_runner.end()
        if not do_not_save and not self.debug_mode:
            self.dc.save(save_csv=False)
            # put_experiment_in_db(self.dc.get_clean_dict())
        self.protocol_runner.reset()

    def closeEvent(self, *args, **kwargs):
        if self.protocol_runner is not None:
            self.end_protocol(do_not_save=True)
        self.app.closeAllWindows()


class LightsheetExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)

        self.chk_lightsheet = QCheckBox("Wait for lightsheet")
        self.chk_lightsheet.setChecked(False)

        self.widget_control.layout.addWidget(self.chk_lightsheet, 0)

        self.lightsheet_config = dict()
        self.dc.add_data_source('imaging', 'lightsheet_config', self, 'lightsheet_config')

    def start_protocol(self):
        # Start only when received the GO signal from the lightsheet
        if self.chk_lightsheet.isChecked():
            self.zmq_socket.bind("tcp://*:5555")
            print('bound socket')
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            print(self.lightsheet_config)
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.protocol_runner.duration)
        super().start_protocol()


class CameraExperiment(Experiment):
    def __init__(self, *args, video_file=None, **kwargs):
        """

        :param args:
        :param video_file: if not using a camera, the video
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.frame_queue = Queue(500)
        self.gui_frame_queue = Queue()
        self.finished_sig = Event()

        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)

        self.metadata_camera = MetadataCamera()
        self.dc.add_data_source(self.metadata_camera)

        if video_file is None:
            self.control_queue = Queue()
            self.camera = XimeaCamera(self.frame_queue,
                                      self.finished_sig,
                                      self.control_queue)
        else:
            self.control_queue = None
            self.camera = VideoFileSource(self.frame_queue,
                                          self.finished_sig,
                                          video_file)

        self.frame_dispatcher = None

    def go_live(self):
        self.camera.start()
        self.gui_refresh_timer.start(1000//60)
        if self.frame_dispatcher is not None:
            self.frame_dispatcher.start()
        sys.excepthook = self.excepthook

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()
        print('Camera process terminated')
        if self.frame_dispatcher is not None:
            self.frame_dispatcher.terminate()
            print('Frame dispatcher terminated')
        self.gui_refresh_timer.stop()


class TailTrackingExperiment(CameraExperiment):
    def __init__(self, *args,
                 tracking_method='angle_sweep',
                 tracking_method_parameters=None,
                 motion_estimation=None, motion_estimation_parameters=None,
                 **kwargs):
        """ An experiment which contains tail tracking,
        base for any experiment that tracks behaviour or employs
        closed loops

        :param args:
        :param tracking_method: the method used to track the tail
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.metadata.params[('fish_metadata', 'embedded')] = True

        # infrastructure for processing data from the camera
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()

        dict_tracking_functions = dict(angle_sweep=tail_trace_ls,
                                       centroid=detect_tail_embedded)

        current_tracking_method_parameters = get_default_args(dict_tracking_functions[tracking_method])
        if tracking_method_parameters is not None:
            current_tracking_method_parameters.update(tracking_method_parameters)

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                                gui_queue=self.gui_frame_queue,
                                                processing_function=dict_tracking_functions[tracking_method],
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=20,
                                                print_framerate=False)

        self.data_acc_tailpoints = QueueDataAccumulator(self.tail_position_queue,
                                                        header_list=['tail_sum'] +
                                                        ['theta_{:02}'.format(i)
                                                         for i in range(
                                                            current_tracking_method_parameters['n_segments'])])

        self.camera_viewer = CameraTailSelection(
            tail_start_points_queue=self.processing_parameter_queue,
            camera_queue=self.gui_frame_queue,
            tail_position_data=self.data_acc_tailpoints,
            update_timer=self.gui_refresh_timer,
            control_queue=self.control_queue,
            camera_parameters=self.metadata_camera,
            tracking_params=current_tracking_method_parameters)

        self.widget_control.layout.insertWidget(0, self.camera_viewer)

        self.dc.add_data_source('tracking',
                                'tail_position', self.camera_viewer, 'roi_dict')
        self.camera_viewer.reset_ROI()

        # start the processes and connect the timers
        self.gui_refresh_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)

        if motion_estimation == 'LSTM':
            self.position_estimator = LSTMLocationEstimator(self.data_acc_tailpoints,
                                                            self.asset_dir + '/' +
                                                            motion_estimation_parameters['model'])

        self.go_live()

    def start_protocol(self):
        self.data_acc_tailpoints.reset()
        super().start_protocol()

    def end_protocol(self, *args, **kwargs):
        self.dc.add_data_source('behaviour', 'tail',
                                self.data_acc_tailpoints.get_dataframe())
        self.dc.add_data_source('stimulus', 'dynamic_parameters',
                                self.protocol.dynamic_log.get_dataframe())
        super().end_protocol(*args, **kwargs)
        self.position_estimator.reset()

    def set_protocol(self, protocol):
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)

    def excepthook(self, exctype, value, tb):
        traceback.print_tb(tb)
        print('{0}: {1}'.format(exctype, value))
        self.finished_sig.set()
        self.camera.terminate()
        self.frame_dispatcher.terminate()


class MovementRecordingExperiment(CameraExperiment):
    """ Experiment where the fish is recorded while it is moving

    """
    def __init__(self, *args, **kwargs):
        self.framestart_queue = Queue()
        self.splitter = QSplitter()
        self.camera_view = CameraViewCalib(camera_queue=self.gui_frame_queue,
                                           update_timer=self.gui_refresh_timer,
                                           control_queue=self.control_queue,
                                           camera_parameters=self.metadata_camera)
        super().__init__(*args, **kwargs)
        self.calibrator = CircleCalibrator()

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