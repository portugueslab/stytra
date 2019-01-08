from collections import deque
from datetime import datetime
from queue import Empty
from multiprocessing import Queue, Event, Value

import cv2
import numpy as np
from numba import jit

from stytra.utilities import FrameProcess
from arrayqueues.shared_arrays import ArrayQueue, TimestampedArrayQueue

from stytra.tracking.tail import CentroidTrackingMethod, AnglesTrackingMethod
from stytra.tracking.eyes import EyeTrackingMethod
from stytra.tracking.fish import FishTrackingMethod
from stytra.tracking.eyes_tail import TailEyesTrackingMethod

from stytra.tracking.preprocessing import Prefilter, BackgroundSubtractor
from time import sleep


def get_tracking_method(name):
    tracking_methods_list = dict(
        tail=CentroidTrackingMethod,
        angle_sweep=AnglesTrackingMethod,
        eyes=EyeTrackingMethod,
        eyes_tail=TailEyesTrackingMethod,
        fish=FishTrackingMethod,
    )
    return tracking_methods_list.get(name, None)


def get_preprocessing_method(name):
    prepmethods = dict(prefilter=Prefilter, bgsub=BackgroundSubtractor)
    return prepmethods.get(name, None)


class FrameDispatcher(FrameProcess):
    """A class which handles taking frames from the camera and processing them,
     as well as dispatching a subset for display

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        in_frame_queue,
        finished_signal: Event = None,
        pipeline=None,
        processing_parameter_queue=None,
        output_queue=None,
        processing_counter: Value = None,
        gui_framerate=30,
        gui_dispatcher=False,
        **kwargs
    ):
        """
        :param in_frame_queue: queue dispatching frames from camera
        :param finished_signal: signal for the end of the acquisition
        :param processing_parameter_queue: queue for function&parameters
        :param gui_framerate: framerate of the display GUI
        """
        super().__init__(**kwargs)

        self.frame_queue = in_frame_queue
        self.gui_queue = TimestampedArrayQueue()  # GUI queue for displaying the image
        self.output_queue = output_queue  # queue for processing output (e.g., pos)
        self.processing_parameter_queue = processing_parameter_queue
        self.processing_counter = processing_counter

        self.finished_signal = finished_signal
        self.gui_framerate = gui_framerate
        self.gui_dispatcher = gui_dispatcher
        self.pipeline_cls = pipeline
        self.pipeline = None

        self.i = 0



    def process_internal(self, frame):
        """Apply processing function to current frame with
        self.processing_parameters as additional inputs.

        Parameters
        ----------
        frame :
            frame to be processed;

        Returns
        -------
        type
            processed output

        """

    def retrieve_params(self):
        while True:
            try:
                param_dict = self.processing_parameter_queue.get(timeout=0.0001)
                self.pipeline.deserialize_params(param_dict)
            except Empty:
                break

    def run(self):
        """Loop where the tracking function runs."""

        self.pipeline = self.pipeline_cls()
        self.pipeline.setup()

        while not self.finished_signal.is_set():

            # Gets the processing parameters from their queue
            self.retrieve_params()

            # Gets frame from its queue, if the input is too fast, drop frames
            # and process the latest, if it is too slow continue:
            try:
                time, frame_idx, frame = self.frame_queue.get(timeout=0.001)
            except Empty:
                continue

            # If a processing function is specified, apply it:

            messages, output = self.pipeline.run(frame)

            for msg in messages:
                self.message_queue.put(msg)

            self.output_queue.put(time, output)

            # calculate the frame rate
            self.update_framerate()

            # put current frame into the GUI queue
            self.send_to_gui(self.pipeline.diagnostic_image or frame)

        return

    def send_to_gui(self, frame):
        """ Sends the current frame to the GUI queue at the appropriate framerate"""
        if self.current_framerate:
            every_x = max(int(self.current_framerate / self.gui_framerate), 1)
        else:
            every_x = 1
        if self.i == 0:
            self.gui_queue.put(frame)
        self.i = (self.i + 1) % every_x


@jit(nopython=True)
def update_bg(bg, current, alpha):
    """

    Parameters
    ----------
    bg :
        
    current :
        
    alpha :
        

    Returns
    -------

    """
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


@jit(nopython=True)
def _compare_to_previous(current, previous):
    """

    Parameters
    ----------
    current :
        
    previous :
        

    Returns
    -------

    """
    n_dif = np.zeros(previous.shape[0], dtype=np.uint32)
    for k in range(previous.shape[0]):
        for i in range(current.shape[0]):
            for j in range(current.shape[1]):
                n_dif[k] += np.bitwise_xor(current[i, j], previous[k, i, j]) // 255
    return n_dif