from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog, QPushButton, QMainWindow, QSplitter

from multiprocessing import Queue, Event
from stytra.hardware.video import XimeaCamera, FrameDispatcher, VideoFileSource
from stytra.tracking import DataAccumulator
from stytra.tracking.tail import detect_tail_new
from stytra.gui.camera_display import CameraTailSelection, CameraViewWidget
import qdarkstyle
import multiprocessing

# class Experiment(QMainWindow):
#     def __init__(self):
#         self.frame_queue = Queue()
#         self.camera_control_queue = Queue()
#         self.gui_frame_queue = Queue()
#         self.processing_paramter_queue = Queue()
#         self.end_event = Event()
#         self.output_queue = Queue()
#
#         self.camera = XimeaCamera(self.frame_queue,
#                                   self.end_event,
#                                   self.camera_control_queue)
#
#         self.frame_dispatcher = FrameDispatcher(self.frame_queue,
#                                                 self.gui_frame_queue,
#                                                 self.end_event,
#                                                 self.output_queue,
#                                                 processing_function=tail_angles,
#                                                 processing_parameter_queue=self.processing_paramter_queue)
#
#         self.camera_viewer = CameraTailSelection(self.processing_paramter_queue,
#                                                  camera_queue=self.gui_frame_queue)

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
        self.videofile = VideoFileSource(self.frame_queue, self.finished_sig,
                                    '/Users/luigipetrucco/Desktop/tail_movement.avi')

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue,
                                           gui_queue=self.gui_frame_queue,
                                           processing_function=detect_tail_new,
                                           processing_parameter_queue=self.processing_parameter_queue,
                                           finished_signal=self.finished_sig,
                                           output_queue=self.tail_position_queue,
                                           gui_framerate=50)



        self.data_accumulator = DataAccumulator(self.tail_position_queue)
        self.camera_viewer = CameraTailSelection(tail_start_points_queue=self.processing_parameter_queue,
                                                 camera_queue=self.gui_frame_queue,
                                                 tail_position_data=self.data_accumulator)
        # camera_viewer=CameraViewWidget(camera_queue=gui_frame_queue)
        self.videofile.start()
        self.frame_dispatcher.start()
        # camera_viewer.show()

        self.main_layout = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.camera_viewer)

        # stopButton = QPushButton('Stop')
        # stopButton.clicked.connect(self.finishProtocol)
        # stopButton.clicked.connect(videofile.join)
        # stopButton.clicked.connect(processing_parameter_queue.close)
        # main_layout.addWidget(stopButton)



        self.setCentralWidget(self.main_layout)
        self.show()

    def finishProtocol(self):

        # self.finished_sig.set()
        # self.videofile.join()
        # print('Camera joined')
        # self.frame_dispatcher.join()
        # print('Frame dispatcher terminated')

        #print(self.data_accumulator.stored_data)
        #self.data_accumulator.get_data()
        #self.data_accumulator.close()
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

if __name__=='__main__':
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    exp = Experiment(app)
    app.exec_()