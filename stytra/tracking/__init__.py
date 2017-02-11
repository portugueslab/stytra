from multiprocessing import Process
from queue import Empty
from stytra.tracking.fish import detect_fishes
import cv2
from datetime import datetime
import numpy as np


class FishTrackingProcess(Process):
    def __init__(self, image_queue, fish_queue, stop_event,
                 processing_parameters, diagnostic_queue=None):
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
        bg_sub = cv2.bgsegm.createBackgroundSubtractorMOG(history=500,
                                                          nmixtures=3,
                                                          backgroundRatio=0.8,
                                                          noiseSigma=2)
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
                    output = detect_fishes(frame, mask.copy(),
                                           params=self.processing_parameters,
                                                       diagnostics=self.diagnostics)
                    if self.diagnostics:
                        fishes, diag_frame = output
                    else:
                        fishes = output
                    self.fish_queue.put((time, fishes))

                    if self.diagnostics:
                        self.diagnostic_queue.put(diag_frame)

                # calculate the framerate
                if i_fps == n_fps_frames - 1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()
                    print('Fish detection runs on {:.2f} FPS'.format(current_framerate))
                    previous_time = current_time
                i_fps = (i_fps + 1) % n_fps_frames
                i_total += 1

            except Empty:
                print('empty_queue ft')

