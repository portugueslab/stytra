from collections import deque
from datetime import datetime
from queue import Empty

import cv2
import numpy as np
import param as pa
import psutil
from numba import jit

from stytra.hardware.video import FrameProcessor


class FrameDispatcher(FrameProcessor):
    """ A class which handles taking frames from the camera and processing them,
     as well as dispatching a subset for display

    """
    def __init__(self, frame_queue, gui_queue, finished_signal=None, output_queue=None,
                 processing_function=None, processing_parameter_queue=None,
                 gui_framerate=30, **kwargs):
        """
        :param frame_queue: queue dispatching frames from camera
        :param gui_queue: queue where to put frames to be displayed on the GUI
        :param finished_signal: signal for the end of the acquisition
        :param output_queue: queue for the output of the function applied on frames
        :param control_queue:
        :param processing_function: function to be applied to each frame
        :param processing_parameter_queue: queue for the parameters to be passed to the function
        :param gui_framerate: framerate of the display GUI
        """
        super().__init__(**kwargs)

        self.frame_queue = frame_queue
        self.gui_queue = gui_queue
        self.finished_signal = finished_signal
        self.i = 0
        self.gui_framerate = gui_framerate
        self.processing_function = processing_function
        self.processing_parameter_queue = processing_parameter_queue
        self.processing_parameters = dict()
        self.output_queue = output_queue
        self.control_queue = None

    def run(self):
        every_x = 10
        i_frame = 100
        while not self.finished_signal.is_set():
            try:
                time, frame = self.frame_queue.get()

                # acquire the processing parameters from a separate queue
                if self.processing_parameter_queue is not None:
                    try:
                        self.processing_parameters = \
                            self.processing_parameter_queue.get(timeout=0.0001)
                    except Empty:
                        pass

                if self.processing_function is not None:
                    output = self.processing_function(frame,
                                                      **self.processing_parameters)
                    self.output_queue.put((datetime.now(), tuple(output)))

                # calculate the frame rate
                self.update_framerate()
                # put the current frame into the GUI queue
                if self.current_framerate:
                    every_x = max(int(self.current_framerate/self.gui_framerate), 1)
                i_frame += 1
                if self.i == 0:
                    self.gui_queue.put((None, frame))
                self.i = (self.i+1) % every_x
            except Empty:
                break

        return


class MovementDetectionParameters(pa.Parameterized):
    fish_threshold = pa.Integer(100, (0, 255))
    motion_threshold = pa.Integer(255*8)
    frame_margin = pa.Integer(10)
    n_previous_save = pa.Integer(400)
    n_next_save = pa.Integer(300)


@jit(nopython=True)
def update_bg(bg, current, alpha):
    am = 1 - alpha
    dif = np.empty_like(current)
    for i in range(current.shape[0]):
        for j in range(current.shape[1]):
            bg[i, j] = bg[i, j] * am + current[i, j] * alpha
            if bg[i, j] > current[i, j]:
                dif[i, j] = bg[i, j] - current[i, j]
            else:
                dif[i, j] = current[i, j] - bg[i, j]
    return dif


class MovingFrameDispatcher(FrameDispatcher):
    def __init__(self, *args, output_queue, control_queue,
                 framestart_queue, signal_start_rec, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_queue = output_queue
        self.control_queue = control_queue
        self.framestart_queue = framestart_queue

        self.signal_start_rec = signal_start_rec
        self.mem_use = 0
        self.processing_parameters = MovementDetectionParameters()

    def run(self):
        i = 0
        every_x = 10

        t, frame_0 = self.frame_queue.get(timeout=5)
        n_previous_compare = 3
        previous_ims = np.zeros((n_previous_compare, ) + frame_0.shape,
                                dtype=np.uint8)

        previous_images = deque()
        record_counter = 0

        i_frame = 0
        recording_state = False

        i_recorded = 0

        while not self.finished_signal.is_set():
            try:

                if self.processing_parameter_queue is not None:
                    try:
                        self.processing_parameters = self.processing_parameter_queue.get(timeout=0.0001)
                    except Empty:
                        pass

                # process frames as they come, threshold them to roughly find the fish (e.g. eyes)
                current_time, current_frame = self.frame_queue.get()
                _, current_frame_thresh =  \
                    cv2.threshold(cv2.boxFilter(current_frame, -1, (3, 3)),
                                  self.processing_parameters.fish_threshold,
                                  255, cv2.THRESH_BINARY)

                # compare the thresholded frame to the previous ones, if there are enough differences
                # because the fish moves, start recording to file
                difsum = 0
                n_crossed = 0
                image_crop = slice(self.processing_parameters.frame_margin, -self.processing_parameters.frame_margin)
                if i_frame >= n_previous_compare:
                    for j in range(n_previous_compare):
                        difsum = cv2.sumElems(cv2.absdiff(previous_ims[j, image_crop, image_crop],
                                                          current_frame_thresh[image_crop, image_crop]))[0]

                        if difsum > self.processing_parameters.motion_threshold:
                            n_crossed += 1

                    if n_crossed == n_previous_compare:
                        record_counter = self.processing_parameters.n_next_save

                    if record_counter > 0:
                        if self.signal_start_rec.is_set() and self.mem_use < 0.9:
                            if not recording_state:
                                while previous_images:
                                    time, im = previous_images.popleft()
                                    self.framestart_queue.put(time)
                                    self.output_queue.put(im)
                                    i_recorded += 1
                            self.output_queue.put(current_frame)
                            self.framestart_queue.put(current_time)
                            i_recorded += 1
                        recording_state = True
                        record_counter -= 1
                    else:
                        recording_state = False
                        previous_images.append((current_time, current_frame))
                        if len(previous_images) > self.processing_parameters.n_previous_save:
                            previous_images.popleft()

                i_frame += 1

                previous_ims[i_frame % n_previous_compare, :, :] = current_frame_thresh

                # calculate the framerate
                self.update_framerate()
                if self.current_framerate is not None:
                    every_x = max(int(self.current_framerate / self.gui_framerate), 1)

                if self.i == 0:
                    self.mem_use = psutil.virtual_memory().used/psutil.virtual_memory().total
                    self.gui_queue.put((current_time, current_frame)) # frame

                self.i = (self.i + 1) % every_x
            except Empty:
                break