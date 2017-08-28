from PyQt5.QtWidgets import QApplication, QMainWindow

from stytra.gui.control_gui import ProtocolControlWindow
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.calibration import CrossCalibrator

from stytra.metadata import MetadataFish, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
from stytra.collectors import DataCollector
import qdarkstyle
import git

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource, FrameDispatcher
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.tail import tail_trace_ls, detect_tail_embedded
from stytra.gui.camera_display import CameraTailSelection
from stytra.gui.plots import StreamingPlotWidget
from multiprocessing import Queue, Event
from stytra.stimulation import Protocol

from PyQt5.QtCore import QTimer, pyqtSignal
from stytra.metadata import MetadataCamera
import sys

import traceback

# imports for accumulator
import pandas as pd
import numpy as np

# imports for moving detector
from stytra.hardware.video import MovingFrameDispatcher

import os

import zmq


# this part is needed to find default arguments of functions
import inspect

def get_default_args(func):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }

class Experiment(QMainWindow):
    sig_calibrating = pyqtSignal()
    def __init__(self, directory, name, calibrator=None,
                 save_csv=False, run_committed=False,
                 app=None):
        """ A general class for running experiments

        :param directory:
        :param name:
        :param app: A QApplication in which to run the experiment
        """
        super().__init__()

        self.app = app

        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.metadata_general = MetadataGeneral()
        self.metadata_fish = MetadataFish()

        self.directory = directory

        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        self.name = name
        self.run_committed = run_committed

        self.save_csv = save_csv

        self.dc = DataCollector(self.metadata_general, self.metadata_fish,
                                folder_path=self.directory, use_last_val=True)

        self.window_display = StimulusDisplayWindow(experiment=self)
        self.widget_control = ProtocolControlWindow(self.window_display)

        self.metadata_gui = MetaListGui([self.metadata_general, self.metadata_fish])
        self.widget_control.button_metadata.clicked.connect(self.metadata_gui.show)
        self.widget_control.button_start.clicked.connect(self.start_protocol)
        self.widget_control.button_end.clicked.connect(self.end_protocol)

        # Connect the display window to the metadata collector
        self.dc.add_data_source('stimulus', 'display_params',
                            self.window_display, 'display_params',
                                use_last_val=True)

        self.window_display.update_display_params()
        self.widget_control.reset_ROI()

        if calibrator is None:
            self.calibrator = CrossCalibrator()
        else:
            self.calibrator = calibrator
        self.window_display.widget_display.calibrator = self.calibrator
        self.widget_control.button_show_calib.clicked.connect(self.toggle_calibration)
        self.dc.add_data_source('stimulus', 'mm per px',
                                self.calibrator, 'mm_px', use_last_val=True)
        self.dc.add_data_source('stimulus', 'calibration_pattern_length_mm',
                                self.calibrator, 'length_mm', use_last_val=True)
        self.dc.add_data_source('stimulus', 'calibration_pattern_length_px',
                                self.calibrator, 'length_px',
                                use_last_val=True)
        self.widget_control.spin_calibrate.valueChanged.connect(
            self.calibrator.set_physical_scale)
        self.widget_control.spin_calibrate.setValue(self.calibrator.length_mm)

        self.protocol = None

    def set_protocol(self, protocol):
        self.protocol = protocol
        self.protocol.reset()
        self.window_display.widget_display.set_protocol(protocol)
        self.protocol.sig_timestep.connect(self.update_progress)
        self.protocol.sig_protocol_finished.connect(self.end_protocol)
        self.widget_control.progress_bar.setMaximum(int(self.protocol.duration))
        self.dc.add_data_source('stimulus', 'log', protocol.log)

    def update_progress(self, i_stim):
        self.widget_control.progress_bar.setValue(int(self.protocol.t))

    def check_if_committed(self):
        """ Checks if the version of stytra used to run the experiment is commited,
        so that for each experiment it is known what code was used to record it

        :return:
        """
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha
        self.dc.add_data_source('general', 'git_hash', git_hash)
        self.dc.add_data_source('general', 'program_name', __file__)

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
        # if self.run_committed:
        #     self.check_if_committed()
        self.protocol.start()

    def end_protocol(self):
        if self.protocol.running:
            self.protocol.end()
            self.dc.save(save_csv=self.save_csv)
            self.protocol.reset()

    def closeEvent(self, *args, **kwargs):
        self.end_protocol()
        self.app.closeAllWindows()

    def toggle_calibration(self):
        self.calibrator.toggle()
        if self.calibrator.enabled:
            self.widget_control.button_show_calib.setText('Hide calibration')
        else:
            self.widget_control.button_show_calib.setText('Show calibration')
        self.window_display.widget_display.update()
        self.sig_calibrating.emit()


class LightsheetExperiment(Experiment):
    def __init__(self, *args, wait_for_lightsheet=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)

        self.lightsheet_config = dict()
        self.wait_for_lightsheet = wait_for_lightsheet

    def start_protocol(self):
        # Start only when received the GO signal from the lightsheet
        if self.wait_for_lightsheet:
            self.zmq_socket.bind("tcp://*:5555")
            print('bound socket')
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            print(self.lightsheet_config)
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.protocol.duration)
        super().start_protocol()


class CameraExperiment(Experiment):
    def __init__(self, *args, video_input=None, **kwargs):
        """

        :param args:
        :param video_input: if not using a camera, the video
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

        if video_input is None:
            self.control_queue = Queue()
            self.camera = XimeaCamera(self.frame_queue,
                                      self.finished_sig,
                                      self.control_queue)
        else:
            self.control_queue = None
            self.camera = VideoFileSource(self.frame_queue,
                                          self.finished_sig,
                                          video_input)

    def go_live(self):
        self.camera.start()
        self.gui_refresh_timer.start(1000//60)

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()
        print('Camera process terminated')


class TailTrackingExperiment(CameraExperiment):
    def __init__(self, *args,
                        tracking_method='angle_sweep',
                        tracking_method_parameters=None, **kwargs):
        """ An experiment which contains tail tracking,
        base for any experiment that tracks behaviour or employs
        closed loops

        :param args:
        :param tracking_method: the method used to track the tail
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.metadata_fish.embedded = True

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

        # GUI elements
        self.stream_plot = StreamingPlotWidget(data_accumulator=self.data_acc_tailpoints)

        self.camera_viewer = CameraTailSelection(
            tail_start_points_queue=self.processing_parameter_queue,
            camera_queue=self.gui_frame_queue,
            tail_position_data=self.data_acc_tailpoints,
            update_timer=self.gui_refresh_timer,
            control_queue=self.control_queue,
            camera_parameters=self.metadata_camera,
            tracking_params=current_tracking_method_parameters)

        self.dc.add_data_source('tracking',
                                'tail_position', self.camera_viewer, 'roi_dict')


        # start the processes and connect the timers
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)

        self.go_live()

    def go_live(self):
        super().go_live()
        self.frame_dispatcher.start()
        sys.excepthook = self.excepthook

    def start_protocol(self):
        self.data_acc_tailpoints.reset()
        super().start_protocol()

    def end_protocol(self):
        self.dc.add_data_source('tracking', 'tail_angles',
                                self.data_acc_tailpoints.get_dataframe())
        self.dc.add_data_source('stimulus', 'dynamic_parameters',
                                self.protocol.dynamic_log.get_dataframe())
        super().end_protocol()


    def set_protocol(self, protocol):
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')
        self.gui_refresh_timer.stop()

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
        super().__init__(*args, **kwargs)
        self.go_live()

        self.frame_dispatcher = MovingFrameDispatcher(self.frame_queue,
                                                      self.gui_frame_queue,
                                                      self.finished_sig,
                                                      output_queue=self.record_queue,
                                                      framestart_queue=self.framestart_queue,
                                                      signal_start_rec=self.start_rec_sig,
                                                      gui_framerate=30)