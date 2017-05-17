from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog, QPushButton, QMainWindow, QSplitter

from multiprocessing import Queue, Event
from stytra.hardware.video import XimeaCamera, FrameDispatcher, VideoFileSource
from stytra.tracking import DataAccumulator
from stytra.tracking.tail import tail_trace_ls
from stytra.gui.camera_display import CameraTailSelection, CameraViewWidget
from stytra.gui.plots import StreamingPlotWidget
from stytra.metadata import MetadataCamera
import qdarkstyle
import multiprocessing


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        multiprocessing.set_start_method('spawn')

        self.app = app

        self.finished = False
        self.frame_queue = Queue()
        self.gui_frame_queue = Queue()
        self.control_queue = Queue()
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()
        self.finished_sig = Event()
        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)
        self.camera_data = MetadataCamera()

        # self.videofile = VideoFileSource(self.frame_queue, self.finished_sig,
        #                             '/Users/luigipetrucco/Desktop/tail_movement.avi')
        self.camera = XimeaCamera(self.frame_queue, self.finished_sig, self.control_queue)

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue, gui_queue=self.gui_frame_queue,
                                                processing_function=tail_trace_ls,
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=10, print_framerate=False)

        self.data_acc_tailpoints = DataAccumulator(self.tail_position_queue)

        self.stream_plot = StreamingPlotWidget(data_accumulator=self.data_acc_tailpoints)

        self.camera_viewer = CameraTailSelection(tail_start_points_queue=self.processing_parameter_queue,
                                                 camera_queue=self.gui_frame_queue,
                                                 tail_position_data=self.data_acc_tailpoints,
                                                 update_timer=self.gui_refresh_timer,
                                                 control_queue=self.control_queue,
                                                 camera_parameters=self.camera_data,
                                                 tracking_params={'num_points': 9, 'width': 10, 'filtering': True})
                                                 # tracking_params={'n_segments': 10, 'window_size': 25,
                                                 #                  'color_invert': False, 'image_filt': True})

        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(self.data_acc_tailpoints.update_list)

        self.camera.start()
        self.frame_dispatcher.start()
        self.gui_refresh_timer.start()

        self.main_layout = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.camera_viewer)
        self.main_layout.addWidget(self.stream_plot)


        self.setCentralWidget(self.main_layout)
        self.show()

    def finishProtocol(self):

        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()

        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')


        print('Camera joined')
        self.gui_refresh_timer.stop()
        print('Timer stopped')

        self.finished = True

    def closeEvent(self, QCloseEvent):
        if not self.finished:
            self.finishProtocol()
            self.app.closeAllWindows()
            self.app.quit()

if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    exp = Experiment(app)
    app.exec_()