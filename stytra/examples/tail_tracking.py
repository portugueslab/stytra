from PyQt5.QtWidgets import QMainWindow

from multiprocessing import Queue, Event
from stytra.hardware.video import XimeaCamera, FrameDispatcher
from stytra.tracking.tail import tail_angles
from stytra.gui.camera_display import CameraTailSelection


class Experiment(QMainWindow):
    def __init__(self):
        self.frame_queue = Queue()
        self.camera_control_queue = Queue()
        self.gui_frame_queue = Queue()
        self.processing_paramter_queue = Queue()
        self.end_event = Event()
        self.output_queue = Queue()

        self.camera = XimeaCamera(self.frame_queue,
                                  self.end_event,
                                  self.camera_control_queue)

        self.frame_dispatcher = FrameDispatcher(self.frame_queue,
                                                self.gui_frame_queue,
                                                self.end_event,
                                                self.output_queue,
                                                processing_function=tail_angles,
                                                processing_parameter_queue=self.processing_paramter_queue)

        self.camera_viewer = CameraTailSelection(self.processing_paramter_queue,
                                                 camera_queue=self.gui_frame_queue)

