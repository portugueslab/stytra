from collections import deque
from datetime import datetime
from queue import Empty
from multiprocessing import Queue

import cv2
import numpy as np
from numba import jit

from stytra.utilities import FrameProcess
from arrayqueues.shared_arrays import ArrayQueue, TimestampedArrayQueue

from stytra.tracking.tail import CentroidTrackingMethod, AnglesTrackingMethod
from stytra.tracking.eyes import EyeTrackingMethod
from stytra.tracking.fish import FishTrackingMethod
from stytra.tracking.eyes_tail import TailEyesTrackingMethod

from stytra.tracking.preprocessing import Prefilter, BackgorundSubtractor, CV2BgSub
from stytra.tracking.movement import MovementDetectionParameters


def get_tracking_method(name):
    tracking_methods_list = dict(
        centroid=CentroidTrackingMethod,
        angle_sweep=AnglesTrackingMethod,
        eye_threshold=EyeTrackingMethod,
        eyes_tail=TailEyesTrackingMethod,
        fish=FishTrackingMethod,
    )
    return tracking_methods_list.get(name, None)


def get_preprocessing_method(name):
    prepmethods = dict(
        prefilter=Prefilter, bgsub=BackgorundSubtractor, bgsubcv=CV2BgSub
    )
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
        finished_signal=None,
        processing_class=None,
        preprocessing_class=None,
        processing_parameter_queue=None,
        gui_framerate=30,
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
        self.output_queue = Queue()  # queue for processing output (e.g., pos)
        self.processing_parameters = dict()

        self.finished_signal = finished_signal
        self.i = 0
        self.gui_framerate = gui_framerate
        self.preprocessing_cls = get_preprocessing_method(preprocessing_class)
        self.tracking_cls = get_tracking_method(processing_class)
        self.processing_parameter_queue = processing_parameter_queue

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

    def run(self):
        """Loop where the tracking function runs."""
        preprocessor = (
            self.preprocessing_cls() if self.preprocessing_cls is not None else None
        )
        tracker = self.tracking_cls()
        while not self.finished_signal.is_set():

            # Gets the processing parameters from their queue
            if self.processing_parameter_queue is not None:
                try:
                    # Read all parameters from the queue:
                    self.processing_parameters.update(
                        **self.processing_parameter_queue.get(timeout=0.0001)
                    )

                except Empty:
                    pass

            # Gets frame from its queue:
            try:
                time, frame = self.frame_queue.get(timeout=0.001)

                # If a processing function is specified, apply it:

                if self.preprocessing_cls is not None:
                    processed = preprocessor.process(
                        frame, **self.processing_parameters
                    )
                else:
                    processed = frame

                if self.tracking_cls is not None:
                    output = tracker.detect(processed, **self.processing_parameters)
                    self.output_queue.put((datetime.now(), output))

                # calculate the frame rate
                self.update_framerate()

                # put current frame into the GUI queue
                if self.processing_parameters.get("display_processed", "raw") != "raw":
                    try:
                        self.send_to_gui(tracker.diagnostic_image)
                    except AttributeError:
                        self.send_to_gui(processed)
                else:
                    self.send_to_gui(frame)

            except Empty:  # if there is nothing in frame queue
                pass
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


class MovingFrameDispatcher(FrameDispatcher):
    """ """

    def __init__(self, *args, signal_start_rec, output_queue_mb=1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.save_queue = ArrayQueue(max_mbytes=output_queue_mb)
        self.framestart_queue = Queue()
        self.diagnostic_queue = Queue()

        self.processing_parameters = MovementDetectionParameters().get_clean_values()

        self.signal_start_rec = signal_start_rec
        self.mem_use = 0

        self.diagnostic_params = [
            "n_pixels_difference",
            "recording_state",
            "n_images_in_buffer",
        ]

    def run(self):
        """ """
        t, frame_0 = self.frame_queue.get(timeout=10)
        n_previous_compare = 3

        image_crop = slice(
            self.processing_parameters["frame_margin"],
            -self.processing_parameters["frame_margin"],
        )

        previous_ims = np.zeros(
            (n_previous_compare,) + frame_0[image_crop].shape, dtype=np.uint8
        )

        image_buffer = deque()
        record_counter = 0

        i_frame = 0
        recording_state = False

        i_recorded = 0

        while not self.finished_signal.is_set():

            # Gets the processing parameters from their queue
            if self.processing_parameter_queue is not None:
                try:
                    self.processing_parameters = self.processing_parameter_queue.get(
                        timeout=0.00001
                    )
                except Empty:
                    pass

            try:
                current_time, current_frame = self.frame_queue.get(timeout=0.001)
                # process frames as they come, threshold them to roughly
                # find the fish (e.g. eyes)
                _, current_frame_thresh = cv2.threshold(
                    cv2.boxFilter(current_frame[image_crop], -1, (3, 3)),
                    self.processing_parameters["fish_threshold"],
                    255,
                    cv2.THRESH_BINARY,
                )
                # compare the thresholded frame to the previous ones,
                # if there are enough differences
                # because the fish moves, start recording to file
                if i_frame >= n_previous_compare:
                    difsum = _compare_to_previous(current_frame_thresh, previous_ims)

                    # put the difference in the diagnostic queue so that
                    # the threshold can be set correctly

                    if np.all(
                        difsum > self.processing_parameters["motion_threshold_n_pix"]
                    ):
                        record_counter = self.processing_parameters["n_next_save"]

                    if record_counter > 0:
                        if self.signal_start_rec.is_set() and self.mem_use < 0.9:
                            if not recording_state:
                                while image_buffer:
                                    time, im = image_buffer.popleft()
                                    self.save_queue.put(im)
                                    self.framestart_queue.put((time, (i_recorded,)))
                                    i_recorded += 1
                            self.save_queue.put(current_frame)
                            self.framestart_queue.put((current_time, (i_recorded,)))
                            i_recorded += 1
                        recording_state = True
                        record_counter -= 1
                    else:
                        recording_state = False
                        image_buffer.append((current_time, current_frame))
                        if (
                            len(image_buffer)
                            > self.processing_parameters["n_previous_save"]
                        ):
                            image_buffer.popleft()

                    self.diagnostic_queue.put(
                        (
                            current_time,
                            (
                                difsum[i_frame % n_previous_compare],
                                recording_state,
                                len(image_buffer),
                            ),
                        )
                    )

                i_frame += 1

                previous_ims[i_frame % n_previous_compare, :, :] = current_frame_thresh

                # calculate the framerate and send frame to gui
                self.update_framerate()
                if self.processing_parameters["show_thresholded"]:
                    self.send_to_gui(current_frame_thresh)
                else:
                    self.send_to_gui(current_frame)

            except Empty:
                pass
