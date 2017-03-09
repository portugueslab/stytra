from PyQt5.QtCore import QObject, QTimer
from multiprocessing import Process
from queue import Empty
from stytra.tracking.fish import detect_fish_midline
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_fish_new
import numpy as np


class DataAccumulator(QObject):
    def __init__(self, data_queue):
        """
        General class for accumulating (for saving or dispatching) data
        out of a multiprocessing queue. Require triggering with some timer.
        :param data_queue: queue from witch to retreive data
        """
        super().__init__()
        # The timer should be an external one to avoid multiple timers
        # into the same process (?):
        # self.timer = QTimer()
        # self.timer.start(1)
        # self.timer.setSingleShot(False)
        # self.timer.timeout.connect(self.update_list)

        self.data_queue = data_queue
        self.stored_data = []

    def update_list(self):
        """Upon calling put all available data into a list.
        """
        collected = 0
        while True:
            try:
                self.stored_data.append(self.data_queue.get(timeout=0.00001))
                collected+=1
            except Empty:
                break

        print(collected)








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
        cv2.bgsegm.createBackgroundSubtractorMOG()
        bg_sub = cv2.bgsegm.createBackgroundSubtractorMOG(history=500,
                                                          nmixtures=3,
                                                          backgroundRatio=self.processing_parameters['background_ratio'],
                                                          noiseSigma=self.processing_parameters['background_noise_sigma'])
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

                    output = detect_fish_midline(frame, mask.copy(),
                                           params=self.processing_parameters)
                    print(output)
                    self.fish_queue.put((time, output))

                    if self.diagnostics:
                        display = frame.copy()
                        for fish in output:
                            display = draw_fish_new(display, fish, self.processing_parameters)
                        self.diagnostic_queue.put(display)
                        print('put display')

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

