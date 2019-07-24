from multiprocessing import Event, Queue
from stytra.collectors import FramerateQueueAccumulator

import qdarkstyle
from PyQt5.QtWidgets import QApplication
from stytra.hardware.video.write import VideoWriter
from stytra.stimulation import Protocol, Pause
from lightparam import Param

from stytra.experiments.tracking_experiments import CameraVisualExperiment
from stytra.tracking.tracking_process import DispatchProcess


class VideoRecordingExperiment(CameraVisualExperiment):
    def __init__(self, *args, **kwargs):
        """
        :param video_file: if not using a camera, the video file
        file for the test input
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

        self.finished_evt = Event()
        self.saving_evt = Event()

        self.frame_dispatcher = DispatchProcess(self.camera.frame_queue,
                                                self.finished_evt,
                                                self.saving_evt)

        # start frame dispatcher process:
        self.frame_dispatcher.start()

        # Create and connect framerate accumulator:
        self.acc_tracking_framerate = FramerateQueueAccumulator(self, self.frame_dispatcher.framerate_queue, name="tracking",
                                                                goal_framerate=kwargs["camera"].get("min_framerate", None))
        self.gui_timer.timeout.connect(self.acc_tracking_framerate.update_list)

        # self.filename_queue = Queue()

        self.set_id()
        self.video_writer = VideoWriter(self.filename_base(),
                                        self.frame_dispatcher.output_frame_queue,
                                        self.finished_evt,
                                        self.saving_evt)

        self.video_writer.start()

    def start_protocol(self):
        self.saving_evt.set()
        self.video_writer.reset_signal.set()
        super().start_protocol()


    def end_protocol(self, save=True):
        self.saving_evt.clear()

        super().end_protocol()

    def wrap_up(self, *args, **kwargs):
        self.video_writer.finished_signal.set()
        self.video_writer.join()
        print("closed")
        super().wrap_up(*args, **kwargs)













