from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog, QPushButton, QMainWindow, QSplitter

from multiprocessing import Queue, Event
from stytra.hardware.video import XimeaCamera, FrameDispatcher, VideoFileSource
from stytra.tracking import DataAccumulator
from stytra.tracking.tail import detect_tail_embedded
from stytra.gui.camera_display import CameraTailSelection, CameraViewWidget
from stytra.gui.plots import TailPlot
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
        self.processing_parameter_queue = Queue()
        self.tail_position_queue = Queue()
        self.finished_sig = Event()
        self.timer = QTimer()
        self.timer.setSingleShot(False)

        self.videofile = VideoFileSource(self.frame_queue, self.finished_sig,
                                    '/Users/luigipetrucco/Desktop/tail_movement.avi')

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                                gui_queue=self.gui_frame_queue,
                                                processing_function=detect_tail_embedded,
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=50)

        self.data_accumulator = DataAccumulator(self.tail_position_queue)

        self.stream_plot = TailPlot(data_accumulator=self.data_accumulator)

        self.camera_viewer = CameraTailSelection(tail_start_points_queue=self.processing_parameter_queue,
                                                 camera_queue=self.gui_frame_queue,
                                                 tail_position_data=self.data_accumulator,
                                                 update_timer=self.timer)
        self.timer.timeout.connect(self.stream_plot.update)
        self.timer.timeout.connect(self.data_accumulator.update_list)
        self.videofile.start()
        self.frame_dispatcher.start()
        self.timer.start()

        self.main_layout = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.camera_viewer)
        self.main_layout.addWidget(self.stream_plot)


        self.setCentralWidget(self.main_layout)
        self.show()

    def finishProtocol(self):

        self.timer.stop()
        print('Timer stopped')

        self.finished_sig.set()
        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')

        self.videofile.terminate()
        print('Camera joined')


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