from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog, QPushButton
import qdarkstyle


from stytra.hardware.cameras import VideoFileSource, BgSepFrameDispatcher, FrameDispatcher
from stytra.tracking.fish import detect_fishes
from functools import partial
from multiprocessing import Queue, Event

import numpy as np

from stytra.gui import control_gui, display_gui, camera_display

def proc(frame, mask):
    return [np.mean(frame), np.mean(mask)]

if __name__ == '__main__':
    experiment_folder = r'\home\vilimstich\PhD\experimental\fishrecordings\stytra'
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    def_params = dict(blurstd=3,
                      thresh_dif=20,
                      target_area=430,
                      area_tolerance=90,
                      length_scaling=3.6,
                      tail_to_body_ratio=0.8,
                      n_tail_segments=10,
                      tail_start_from_eye_centre=0.2,
                      eye_area_ratio=0.02,
                      eye_aspect=0.9,
                      eye_threshold=50)

    frame_queue = Queue()
    gui_frame_queue = Queue()
    data_queue = Queue()
    finished_sig = Event()

    camera = VideoFileSource(frame_queue, finished_sig,
                              '/Users/vilimstich/PhD/TempData/Fish_recordings/Long_days/20160511T145418m.avi')
    fish_detector = partial(detect_fishes, params=def_params)

    frame_dispatcher = BgSepFrameDispatcher(frame_queue,
                                            gui_frame_queue,
                                            output_queue = data_queue,
                                            processing_function = detect_fishes,
                                            processing_parameters = def_params)

    win_main = QDialog()
    main_layout = QHBoxLayout()
    camera_view = camera_display.CameraViewCalib(gui_frame_queue)
    main_layout.addWidget(camera_view)

    stopButton = QPushButton('Stop')
    stopButton.clicked.connect(finished_sig.set)
    main_layout.addWidget(stopButton)

    win_main.setLayout(main_layout)
    win_main.show()

    camera.start()
    frame_dispatcher.start()



    app.exec_()

