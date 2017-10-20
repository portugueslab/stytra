from PyQt5.QtCore import QObject
from multiprocessing import Process
from queue import Empty
from stytra.tracking.fish import find_fishes_midlines
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_found_fish
from stytra.collectors import Accumulator


class QueueDataAccumulator(QObject, Accumulator):
    def __init__(self, data_queue, header_list=None):
        """
        General class for accumulating (for saving or dispatching) data
        out of a multiprocessing queue. Require triggering with some timer.
        This timer has to be set externally!!!
        :param data_queue: queue from witch to retrieve data (Queue object)
        :param header_list: headers for the data that will be stored (strings list)
        """
        super().__init__()

        # Store externally the starting time make us free to keep
        # only time differences in milliseconds in the list (faster)
        self.starting_time = None

        self.data_queue = data_queue
        self.stored_data = []

        # First data column will always be time:
        self.header_list.extend(header_list)

    def update_list(self):
        """Upon calling put all available data into a list.
        """
        while True:
            try:
                # Get data from queue:
                t, data = self.data_queue.get(timeout=0.00001)

                # If we are at the starting time:
                if len(self.stored_data) == 0:
                    self.starting_time = t

                # Time in ms (for having np and not datetime objects)
                t_ms = (t - self.starting_time).total_seconds()

                # append:
                self.stored_data.append((t_ms, ) + data)
            except Empty:
                break



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
                    self.fish_queue.put((time, output))

                    if self.diagnostics:
                        display = frame.copy()
                        for fish in output:
                            display = draw_fish_new(display, fish, self.processing_parameters)
                        self.diagnostic_queue.put(display)

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
                pass

