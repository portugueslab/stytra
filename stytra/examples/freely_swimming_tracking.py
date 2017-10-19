from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog, QPushButton
import qdarkstyle

from stytra.hardware.video import VideoFileSource
from stytra import FrameDispatcher
from stytra.tracking import FishTrackingProcess
from stytra.tracking.fish import detect_fish_midline, MidlineDetectionParams
from functools import partial
from multiprocessing import Queue, Event

import numpy as np

from stytra.gui import protocol_control, stimulus_display, camera_display

def proc(frame, mask):
    return [np.mean(frame), np.mean(mask)]

if __name__ == '__main__':
    experiment_folder = r'\home\vilimstich\PhD\experimental\fishrecordings\stytra'
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    frame_queue = Queue()
    fish_frame_queue = Queue()
    gui_frame_queue = Queue()
    data_queue = Queue()
    finished_sig = Event()

    camera = VideoFileSource(frame_queue, finished_sig,
                              '/Users/vilimstich/PhD/Experimental/stytra_recordings/testlight.avi')

    frame_dispatcher = FrameDispatcher(frame_queue,
                                        fish_frame_queue,
                                       finished_sig, gui_framerate=100)

    detection_params = MidlineDetectionParams()
    tracker = FishTrackingProcess(fish_frame_queue, data_queue, finished_sig,
                                  detection_params.get_param_dict(), gui_frame_queue)

    win_main = QDialog()
    main_layout = QHBoxLayout()
    camera_view = camera_display.CameraViewWidget(gui_frame_queue)
    main_layout.addWidget(camera_view)

    stopButton = QPushButton('Stop')
    stopButton.clicked.connect(finished_sig.set)
    main_layout.addWidget(stopButton)

    win_main.setLayout(main_layout)
    win_main.show()

    camera.start()
    frame_dispatcher.start()
    tracker.start()


    app.exec_()

