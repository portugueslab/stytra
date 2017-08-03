from PyQt5.QtWidgets import QApplication, QMainWindow

from stytra.gui.control_gui import ProtocolControlWindow
from stytra.gui.display_gui import StimulusDisplayWindow

from stytra.metadata import MetadataFish, MetadataGeneral
from stytra.collectors import DataCollector
import qdarkstyle
import git

# imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource, FrameDispatcher
from stytra.tracking import DataAccumulator
from stytra.tracking.tail import tail_trace_ls, detect_tail_embedded
from stytra.gui.camera_display import CameraTailSelection
from stytra.gui.plots import StreamingPlotWidget
from multiprocessing import Queue, Event
from stytra.stimulation import Protocol

from PyQt5.QtCore import QTimer
from stytra.metadata import MetadataCamera
import sys

# imports for accumulator
import pandas as pd
import numpy as np

# imports for moving detector
from stytra.hardware.video import MovingFrameDispatcher

import os


class Experiment(QMainWindow):
    def __init__(self, directory, name, save_csv=False, app=None):
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

        self.save_csv = save_csv

        self.dc = DataCollector(self.metadata_general, self.metadata_fish,
                                folder_path=self.directory, use_last_val=True)

        self.window_display = StimulusDisplayWindow()
        self.widget_control = ProtocolControlWindow(self.window_display)

        # Connect the display window to the metadata collector
        self.dc.add_data_source('stimulus', 'display_params',
                                self.window_display.display_params)
        self.window_display.update_display_params()
        self.widget_control.reset_ROI()

        self.protocol = None

    def set_protocol(self, protocol):
        self.protocol = protocol
        self.window_display.set_protocol(protocol)
        self.widget_control.set_protocol(protocol)
        self.protocol.sig_timestep.connect(self.update_progress)
        self.protocol.sig_protocol_finished.connect(self.end_protocol)
        self.widget_control.progress_bar.setMaximum(int(self.protocol.duration))

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

    def end_protocol(self):
        self.dc.save(save_csv=self.save_csv)

    def closeEvent(self, QCloseEvent):
        pass
        #self.end_protocol()
        #self.app.closeAllWindows()


class CameraExperiment(Experiment):
    def __init__(self, *args, video_input=None, **kwargs):
        """

        :param args:
        :param video_input: if not using a camera, the video
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.frame_queue = Queue()
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
        self.gui_refresh_timer.start()

    def end_protocol(self):
        super().end_protocol()
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()


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

        # infrastructure for processing data from the camera
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()

        dict_tracking_functions = dict(angle_sweep=tail_trace_ls,
                                       centroid=detect_tail_embedded)

        if tracking_method_parameters is None:
            tracking_method_parameters = dict()

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                                gui_queue=self.gui_frame_queue,
                                                processing_function=dict_tracking_functions[tracking_method],
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=10,
                                                print_framerate=False)

        self.data_acc_tailpoints = DataAccumulator(self.tail_position_queue)


        # GUI elements
        self.stream_plot = StreamingPlotWidget(data_accumulator=self.data_acc_tailpoints)

        self.camera_viewer = CameraTailSelection(
            tail_start_points_queue=self.processing_parameter_queue,
            camera_queue=self.gui_frame_queue,
            tail_position_data=self.data_acc_tailpoints,
            update_timer=self.gui_refresh_timer,
            control_queue=self.control_queue,
            camera_parameters=self.metadata_camera,
            tracking_params=tracking_method_parameters)

        self.dc.add_data_source('tracking','tail_position', self.camera_viewer.roi_dict)

        # start the processes and connect the timers
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)

        self.go_live()

    def go_live(self):
        super().go_live()
        self.frame_dispatcher.start()

        sys.excepthook = self.excepthook
        self.finished = False

    def set_protocol(self, protocol):
        super().set_protocol(protocol)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)

    def end_protocol(self):
        self.finished = True
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()

        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')

        print('Camera joined')
        self.gui_refresh_timer.stop()

        super().end_protocol()

    def excepthook(self, exctype, value, traceback):
        print(exctype, value, traceback)
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