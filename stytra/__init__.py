from PyQt5.QtWidgets import QApplication
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.metadata import MetadataFish, MetadataGeneral, DataCollector
import qdarkstyle
import git

#imports for tracking
from stytra.hardware.video import XimeaCamera, VideoFileSource, FrameDispatcher
from stytra.tracking import DataAccumulator
from stytra.tracking.tail import tail_trace_ls
from stytra.gui.camera_display import CameraTailSelection
from stytra.gui.plots import StreamingPlotWidget
from multiprocessing import Queue, Event

from PyQt5.QtCore import QTimer
from stytra.metadata import MetadataCamera


class Experiment:
    def __init__(self, directory, name, app=None):
        """ A general class for running experiments

        :param directory:
        :param name:
        :param app: A QApplication in which to run the experiment
        """
        if app is None:
            self.app = QApplication([])
        else:
            self.app = app

        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.metadata_general = MetadataGeneral()
        self.metadata_fish = MetadataFish()

        self.directory = directory
        self.name = name

        self.dc = DataCollector(self.metadata_general, self.metadata_fish,
                                folder_path=self.directory, use_last_val=True)

    def check_if_commited(self):
        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha
        self.data_collector.add_data_source('general', 'git_hash', git_hash)
        self.data_collector.add_data_source('general', 'program_name', __file__)

        if len(repo.git.diff('HEAD~1..HEAD',
                             name_only=True)) > 0:
            print('The following files contain uncommitted changes:')
            print(repo.git.diff('HEAD~1..HEAD', name_only=True))
            raise PermissionError(
                'The project has to be committed before starting!')


    def end_protocol(self):
        self.dc.save(save_csv=False)


class TailTrackingExperiment(Experiment):
    def __init__(self, *args, video_input=None,
                        tracking_method='ts', **kwargs):
        """ An experiment which contains tail tracking,
        base for any experiment that tracks behaviour or employs
        closed loops

        :param args:
        :param video_input: if not using a camera, the video
        file for the test imput
        :param tracking_method: the method used to track the tail
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

        # infrastructure for processing data from the camera
        self.frame_queue = Queue()
        self.gui_frame_queue = Queue()
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()
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

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                                gui_queue=self.gui_frame_queue,
                                                processing_function=tail_trace_ls,
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
            tracking_params={'num_points': 9, 'width': 30, 'filtering': True})

        # start the processes and connect the timers
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(
            self.data_acc_tailpoints.update_list)

        self.camera.start()
        self.frame_dispatcher.start()
        self.gui_refresh_timer.start()

    def end_protocol(self):
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()

        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')

        print('Camera joined')
        self.gui_refresh_timer.stop()

        super().end_protocol()



