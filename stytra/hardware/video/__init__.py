"""
Module to interact with video surces as cameras or video files. It also
implement video saving
"""

import numpy as np

from multiprocessing import Queue, Event
from multiprocessing.queues import Empty
from stytra.utilities import FrameProcess
from arrayqueues.shared_arrays import IndexedArrayQueue
import deepdish as dd

from stytra.hardware.video.cameras import (
    XimeaCamera,
    AvtCamera,
    SpinnakerCamera,
    MikrotronCLCamera,
)

from stytra.hardware.video.write import VideoWriter
from stytra.hardware.video.interfaces import (
    CameraControlParameters,
    VideoControlParameters,
)

from stytra.hardware.video.ring_buffer import RingBuffer

import time


class VideoSource(FrameProcess):
    """Abstract class for a process that generates frames, being it a camera
    or a file source. A maximum size of the memory used by the process can be
    set.
    
    **Input Queues:**

    self.control_queue :
        queue with control parameters for the source, e.g. from a
        :class:`CameraControlParameters <.interfaces.CameraControlParameters>`
        object.


    **Output Queues**

    self.frame_queue :
        TimestampedArrayQueue from the arrayqueues module
        where the frames read from the camera are sent.


    **Events**

    self.kill_signal :
        When set kill the process.


    Parameters
    ----------
    rotation : int
        n of times image should be rotated of 90 degrees
    max_mbytes_queue : int
        maximum size of camera queue (Mbytes)

    Returns
    -------

    """

    def __init__(self, rotation=False, max_mbytes_queue=100, n_consumers=1):
        """ """
        super().__init__()
        self.rotation = rotation
        self.control_queue = Queue()
        self.frame_queue = IndexedArrayQueue(max_mbytes=max_mbytes_queue)
        self.kill_event = Event()
        self.n_consumers = 1


class CameraSource(VideoSource):
    """Process for controlling a camera.

    Cameras currently implemented:
    
    ======== ===========================================
    Ximea    Add some info
    Avt      Add some info
    ======== ===========================================

    Parameters
    ----------
    camera_type : str
        specifies type of the camera (currently supported: 'ximea', 'avt')
    downsampling : int
        specifies downsampling factor for the camera.

    Returns
    -------

    """

    camera_class_dict = dict(
        ximea=XimeaCamera,
        avt=AvtCamera,
        spinnaker=SpinnakerCamera,
        mikrotron=MikrotronCLCamera,
    )
    """ dictionary listing classes used to instantiate camera object."""

    def __init__(
        self, camera_type, *args, downsampling=1, roi=(-1, -1, -1, -1), **kwargs
    ):
        """ """
        super().__init__(*args, **kwargs)

        self.camera_type = camera_type
        self.downsampling = downsampling
        self.roi = roi
        self.control_params = CameraControlParameters
        self.replay = False
        self.replay_fps = 0
        self.cam = None
        self.paused = False
        self.ring_buffer = None  # RingBuffer(600) # TODO make it parameterized

    def run(self):
        """
        After initializing the camera, the process constantly does the
        following:

            - read control parameters from the control_queue and set them;
            - read frames from the camera and put them in the frame_queue.


        """
        try:
            CameraClass = self.camera_class_dict[self.camera_type]
            self.cam = CameraClass(downsampling=self.downsampling, roi=self.roi)
        except KeyError:
            raise Exception("{} is not a valid camera type!".format(self.camera_type))
        self.message_queue.put("I:" + str(self.cam.open_camera()))
        prt = None
        while True:
            # Kill if signal is set:
            self.kill_event.wait(0.0001)
            if self.kill_event.is_set():
                break

            # Try to get new parameters from the control queue:
            message = ""
            if self.control_queue is not None:
                while True:
                    try:
                        param_dict = self.control_queue.get(timeout=0.0001)
                        self.replay_fps = param_dict.get("replay_fps", self.replay_fps)
                        self.replay = param_dict.get("replay", self.replay)
                        self.paused = param_dict.get("paused", self.paused)
                        for param, value in param_dict.items():
                            message = self.cam.set(param, value)
                    except Empty:
                        break

            # Grab the new frame, and put it in the queue if valid:
            arr = self.cam.read()
            if self.rotation:
                arr = np.rot90(arr, self.rotation)
            if self.ring_buffer is None:
                self.ring_buffer = RingBuffer(300)
            self.ring_buffer.put(arr)

            self.update_framerate()

            if self.replay and self.replay_fps>0:
                try:
                    self.frame_queue.put(self.ring_buffer.get())
                except ValueError:
                    pass
                delta_t = 1 / self.replay_fps
                if prt is not None:
                    extrat = delta_t - (time.process_time() - prt)
                    if extrat > 0:
                        time.sleep(extrat)
                prt = time.process_time()
            else:
                prt = None
                if arr is not None and not self.paused:
                    # If the queue is full, arrayqueues should print a warning!
                    if self.frame_queue.queue.qsize() < self.n_consumers + 2:
                        self.frame_queue.put(arr)
                    else:
                        self.message_queue.put("W:Dropped frame")

        self.cam.release()


class VideoFileSource(VideoSource):
    """A class to stream videos from a file to test parts of
    stytra without a camera available, or do offline analysis

    Parameters
    ----------
        source_file
            path of the video file
        loop : bool
            continue video from the beginning if the end is reached

    Returns
    -------

    """

    def __init__(self, source_file=None, loop=True, framerate=None, **kwargs):
        super().__init__(**kwargs)
        self.source_file = source_file
        self.loop = loop
        self.framerate = framerate
        self.control_params = VideoControlParameters
        self.offset = 0
        self.paused = False
        self.old_frame = None
        self.offset = 0


    def inner_loop(self):
        pass

    def run(self):

        if self.source_file.endswith("h5"):
            framedata = dd.io.load(self.source_file)
            frames = framedata["video"]
            if self.framerate is None:
                delta_t = 1 / framedata.get("framerate", 30.0)
            else:
                delta_t = 1 / self.framerate
            i_frame = self.offset
            prt = None
            while not self.kill_event.is_set():

                # Try to get new parameters from the control queue:
                message = ""
                if self.control_queue is not None:
                    while True:
                        try:
                            param_dict = self.control_queue.get(timeout=0.0001)
                            for name, value in param_dict.items():
                                if name == "framerate":
                                    delta_t = 1 / value
                                elif name == "offset":
                                    if value != self.offset:
                                        self.offset = value
                                elif name == "paused":
                                    self.paused = value
                        except Empty:
                            break

                # we adjust the framerate
                if prt is not None:
                    extrat = delta_t - (time.process_time() - prt)
                    if extrat > 0:
                        time.sleep(extrat)

                self.frame_queue.put(frames[i_frame, :, :])
                if not self.paused:
                    i_frame += 1
                if i_frame == frames.shape[0]:
                    if self.loop:
                        i_frame = self.offset
                    else:
                        break
                self.update_framerate()
                prt = time.process_time()
        else:
            import cv2

            cap = cv2.VideoCapture(self.source_file)
            ret = True

            if self.framerate is None:
                try:
                    delta_t = 1 / cap.get(cv2.CAP_PROP_FPS)
                except ZeroDivisionError:
                    delta_t = 1 / 30
            else:
                delta_t = 1 / self.framerate

            prt = None
            while ret and not self.kill_event.is_set():
                if self.paused:
                    ret = True
                    frame = self.old_frame
                else:
                    ret, frame = cap.read()

                # adjust the frame rate by adding extra time if the processing
                # is quicker than the specified framerate

                if self.control_queue is not None:
                    try:
                        param_dict = self.control_queue.get(timeout=0.0001)
                        for name, value in param_dict.items():
                            if name == "framerate":
                                delta_t = 1 / value
                            elif name == "offset":
                                if value != self.offset:
                                    cap.set(cv2.CAP_PROP_POS_FRAMES, value)
                                    self.offset = value
                            elif name == "paused":
                                self.paused = value
                    except Empty:
                        pass

                if prt is not None:
                    extrat = delta_t - (time.process_time() - prt)
                    if extrat > 0:
                        time.sleep(extrat)

                if ret:
                    self.frame_queue.put(frame[:, :, 0])
                else:
                    if self.loop:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret = True
                    else:
                        break

                prt = time.process_time()
                self.old_frame = frame
                self.update_framerate()
            return
