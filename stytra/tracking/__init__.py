from multiprocessing import Process
from queue import Empty
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_found_fish
from stytra.utilities import HasPyQtGraphParams


class ParametrizedImageproc():
    def process(self, im, state=None, **kwargs):
        return im

    def reset_state(self):
        pass


class FishTrackingProcess(Process):
    """ """

    def __init__(
        self,
        image_queue,
        fish_queue,
        stop_event,
        processing_parameters,
        diagnostic_queue=None,
    ):
        super().__init__()
        self.image_queue = image_queue
        self.fish_queue = fish_queue
        self.stop_event = stop_event
        self.diagnostic_queue = diagnostic_queue
        if self.diagnostic_queue is not None:
            self.diagnostics = True
        else:
            self.diagnostics = False
        self.processing_parameters = processing_parameters

    def run(self):
        """ """
        cv2.bgsegm.createBackgroundSubtractorMOG()
        bg_sub = cv2.bgsegm.createBackgroundSubtractorMOG(
            history=500,
            nmixtures=3,
            backgroundRatio=self.processing_parameters["background_ratio"],
            noiseSigma=self.processing_parameters["background_noise_sigma"],
        )
        i_total = 0
        n_learn_background = 100
        n_every_bg = 100
        n_fps_frames = 50
        i_fps = 0
        previous_time = datetime.now()
        while not self.stop_event.is_set():
            try:
                indata = self.image_queue.get(timeout=1)
                if isinstance(indata, tuple):
                    time, frame = indata
                else:
                    time = datetime.now()
                    frame = indata

                if i_total < n_learn_background or i_fps % n_every_bg == 0:
                    lr = 0.01
                else:
                    lr = 0

                mask = bg_sub.apply(frame, learningRate=lr)
                if i_total > n_learn_background:

                    output = detect_fish_midline(
                        frame, mask.copy(), params=self.processing_parameters
                    )
                    self.fish_queue.put((time, output))

            except Empty:
                pass
