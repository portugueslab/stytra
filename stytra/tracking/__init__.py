from PyQt5.QtCore import QObject, QTimer
from multiprocessing import Process
from queue import Empty
from stytra.tracking.fish import detect_fish_midline
import cv2
from datetime import datetime
from stytra.tracking.diagnostics import draw_fish_new
import numpy as np
import pandas as pd


class DataAccumulator(QObject):
    def __init__(self, data_queue, header_list=['tail_sum']):
        """
        General class for accumulating (for saving or dispatching) data
        out of a multiprocessing queue. Require triggering with some timer.
        This timer has to be set externally!!!
        :param data_queue: queue from witch to retreive data (Queue object)
        :param header_list: headers for the data that will be stored (stings list)
        """
        super().__init__()

        # Store externally the starting time make us free to keep
        # only time differences in milliseconds in the list (faster)
        self.starting_time = None

        self.data_queue = data_queue
        self.stored_data = []

        # Flag for saving time at the first data retrieval
        self.save_as_first = True

        # First data column will always be time:
        self.header_list = ['time'] + header_list

    def update_list(self):
        """Upon calling put all available data into a list.
        """
        collected = 0
        while True:
            try:
                # Get data from queue:
                t, data = self.data_queue.get(timeout=0.00001)

                # If we are at the starting time:
                if self.save_as_first:
                    self.starting_time = t
                    self.save_as_first = False

                # Time in ms (for having np and not datetime objects)
                t_ms = (t - self.starting_time).total_seconds()

                # append:
                self.stored_data.append([t_ms, ] + data)
                collected += 1
            except Empty:
                break

    def reset(self):
        self.stored_data = []
        self.save_as_first = True

    def get_dataframe(self):
        """Returns pandas dataframe with data and headers
        """
        data_array = pd.lib.to_object_array(self.stored_data).astype(float)
        return pd.DataFrame(data_array[:, :len(self.header_list)],
                            columns=self.header_list)
        #time_arr = np.array([(t - time_tuple[0]).total_seconds()
        #                     for t in time_tuple])
        #tail_arr = np.array(data_tuple)
        #return time_arr, tail_arr







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

