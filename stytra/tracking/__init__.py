from multiprocessing import Process
from queue import Empty
from stytra.tracking.fish import detect_fishes
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_fish
import numpy as np

class FishTrackingProcess(Process):
    def __init__(self, image_queue, fish_queue, stop_event,
                 processing_parameters, diagnostic_queue=None):
        super().__init__()
        self.image_queue = image_queue
        self.fish_queue = fish_queue
        self.stop_event = stop_event
        self.diagnostic_queue = diagnostic_queue
        self.processing_parameters = processing_parameters

    def run(self):
        bg_sub = cv2.bgsegm.createBackgroundSubtractorMOG(history=500,
                                                          nmixtures=3,
                                                          backgroundRatio=0.8,
                                                          noiseSigma=2)
        i_total = 0
        n_learn_background = 100
        n_every_bg = 500
        n_fps_frames = 50
        i_fps = 0
        previous_time = datetime.now()
        while not self.stop_event.is_set():
            try:
                frame = self.image_queue.get(timeout=1)
                if i_total < n_learn_background or i_fps % n_every_bg == 0:
                    lr = 0.01
                else:
                    lr = 0

                mask = bg_sub.apply(frame, learningRate=lr)
                if i_total > n_learn_background:
                    fishes = detect_fishes(frame, mask.copy(),
                                                      params=self.processing_parameters)
                    self.fish_queue.put(fishes)
                    if self.diagnostic_queue is not None:
                        display = np.vstack([frame, mask])

                        for fish in fishes:
                            draw_fish(display,fish,self.processing_parameters)
                        self.diagnostic_queue.put(display)
                # calculate the framerate
                if i_fps == n_fps_frames - 1:
                    current_time = datetime.now()
                    current_framerate = n_fps_frames / (
                        current_time - previous_time).total_seconds()
                    # print('{:.2f} FPS'.format(framerate))
                    previous_time = current_time
                i_fps = (i_fps + 1) % n_fps_frames
                i_total += 1

            except Empty:
                print('empty_queue ft')

