"""
Module to interact with video surces as cameras or video files. It also
implement video saving
"""

import numpy as np

from multiprocessing import Queue, Event
from queue import Empty

from lightparam import Param
from lightparam.param_qt import ParametrizedQt

from stytra.utilities import FrameProcess
from arrayqueues.shared_arrays import IndexedArrayQueue
import deepdish as dd

from stytra.hardware.video.cameras import camera_class_dict

from stytra.hardware.video.write import VideoWriter

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

    def __init__(self, rotation=False, max_mbytes_queue=200, n_consumers=1):
        """ """
        super().__init__(name="camera")
        self.rotation = rotation
        self.control_queue = Queue()
        self.frame_queue = IndexedArrayQueue(max_mbytes=max_mbytes_queue)
        self.kill_event = Event()
        self.n_consumers = 1
        self.state = None


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

    """ dictionary listing classes used to instantiate camera object."""

    def __init__(
        self, camera_type, *args, downsampling=1, roi=(-1, -1, -1, -1),
            max_buffer_length=1000,
            **kwargs
    ):
        """ """
        super().__init__(*args, **kwargs)

        self.cam = None

        self.camera_type = camera_type
        self.downsampling = downsampling
        self.roi = roi

        self.max_buffer_length = max_buffer_length

        self.state = None
        self.ring_buffer = None

    def retrieve_params(self, messages):
        while True:
            try:
                param_dict = self.control_queue.get(timeout=0.0001)
                self.state.params.values = param_dict
                for param, value in param_dict.items():
                    ms = self.cam.set(param, value)
                    try:
                        messages.extend(list(ms))
                    except TypeError:
                        pass
            except Empty:
                break

    def run(self):
        """
        After initializing the camera, the process constantly does the
        following:

            - read control parameters from the control_queue and set them;
            - read frames from the camera and put them in the frame_queue.


        """
        if self.state is None:
            self.state = CameraControlParameters()
        try:
            CameraClass = camera_class_dict[self.camera_type]
            self.cam = CameraClass(downsampling=self.downsampling, roi=self.roi)
        except KeyError:
            raise Exception("{} is not a valid camera type!".format(self.camera_type))
        camera_messages = list(self.cam.open_camera())
        [self.message_queue.put(m) for m in camera_messages]
        prt = None
        while True:
            # Kill if signal is set:
            self.kill_event.wait(0.0001)
            if self.kill_event.is_set():
                break
            # Try to get new parameters from the control queue:
            messages = []
            if self.control_queue is not None:
                self.retrieve_params(messages)
            # Grab the new frame, and put it in the queue if valid:
            arr = self.cam.read()
            if self.rotation:
                arr = np.rot90(arr, self.rotation)

            res_len = int(round(self.state.framerate*self.state.ring_buffer_length))
            if res_len > self.max_buffer_length:
                res_len = self.max_buffer_length
                self.message_queue.put("W:Replay buffer too big, make the plot"
                                       " time range smaller for full replay"
                                       " capabilities")

            if self.ring_buffer is None or res_len != self.ring_buffer.length:
                self.ring_buffer = RingBuffer(res_len)

            if self.state.paused:
                self.message_queue.put(
                    "I:Ring_buffer_size:" + str(self.ring_buffer.length)
                )
                if self.ring_buffer.arr is not None:
                    self.frame_queue.put(self.ring_buffer.get_most_recent())
                else:
                    self.message_queue.put(
                        "E:camera paused before any frames acquired")
                prt = None
            elif self.state.replay and self.state.replay_fps > 0:
                messages.append(
                    "I:Replaying between {} and {} of {}".format(
                        *self.state.replay_limits, self.ring_buffer.length
                    )
                )
                old_fps = self.framerate_rec.current_framerate
                if old_fps is not None:
                    self.ring_buffer.replay_limits = (
                        int(round(self.state.replay_limits[0] * old_fps)),
                        int(round(self.state.replay_limits[1] * old_fps)),
                    )
                try:
                    self.frame_queue.put(self.ring_buffer.get())
                except ValueError:
                    pass
                delta_t = 1 / self.state.replay_fps
                if prt is not None:
                    extrat = delta_t - (time.process_time() - prt)
                    if extrat > 0:
                        time.sleep(extrat)
                prt = time.process_time()
            else:
                prt = None
                if arr is not None:
                    try:
                        self.ring_buffer.put(arr)
                    except AttributeError:
                        pass
                    # If the queue is full, arrayqueues should print a warning!
                    if self.frame_queue.queue.qsize() < self.n_consumers + 2:
                        self.frame_queue.put(arr)
                    else:
                        messages.append("W:Dropped frame")
                    self.update_framerate()
            for m in messages:
                self.message_queue.put(m)

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

    def __init__(self, source_file=None, loop=True, **kwargs):
        super().__init__(**kwargs)
        self.source_file = source_file
        self.loop = loop
        self.state = None
        self.offset = 0
        self.paused = False
        self.old_frame = None
        self.offset = 0

    def inner_loop(self):
        pass

    def update_params(self):
        while True:
            try:
                param_dict = self.control_queue.get(timeout=0.0001)
                self.state.params.values = param_dict
            except Empty:
                break

    def run(self):
        if self.state is None:
            self.state = VideoControlParameters()
        if self.source_file.endswith("h5"):
            framedata = dd.io.load(self.source_file)
            frames = framedata["video"]
            i_frame = self.offset
            prt = None
            while not self.kill_event.is_set():

                # Try to get new parameters from the control queue:
                message = ""
                if self.control_queue is not None:
                    self.update_params()

                # we adjust the framerate
                delta_t = 1 / self.state.framerate
                if prt is not None:
                    extrat = delta_t - (time.process_time() - prt)
                    if extrat > 0:
                        time.sleep(extrat)

                self.frame_queue.put(frames[i_frame, :, :])
                if not self.state.paused:
                    i_frame += 1
                if i_frame == frames.shape[0]:
                    if self.loop:
                        i_frame = self.offset
                    else:
                        break
                self.update_framerate()
                prt = time.process_time()

        else:
            import av

            container = av.open(self.source_file)
            container.streams.video[0].thread_type = "AUTO"
            container.streams.video[0].thread_count = 1

            prt = None
            while self.loop:
                for framedata in container.decode(video=0):
                    if self.paused:
                        frame = self.old_frame
                    else:
                        frame = framedata.to_ndarray(format="rgb24")

                    # adjust the frame rate by adding extra time if the processing
                    # is quicker than the specified framerate

                    if self.control_queue is not None:
                        self.update_params()

                    delta_t = 1 / self.state.framerate
                    if prt is not None:
                        extrat = delta_t - (time.process_time() - prt)
                        if extrat > 0:
                            time.sleep(extrat)

                    self.frame_queue.put(frame[:, :, 0])

                    prt = time.process_time()
                    self.old_frame = frame
                    self.update_framerate()
                container.seek(0, whence="frame")

            return


class VideoControlParameters(ParametrizedQt):
    def __init__(self, **kwargs):
        super().__init__(name="video_params", **kwargs)
        self.framerate = Param(100., limits=(10, 700), unit="Hz", desc="Framerate (Hz)")
        self.offset = Param(50)
        self.paused = Param(False)


class CameraControlParameters(ParametrizedQt):
    """HasPyQtGraphParams class for controlling the camera params.
    Ideally, methods to automatically set dynamic boundaries on frame rate and
    exposure time can be implemented. Currently not implemented.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, **kwargs):
        super().__init__(name="camera_params", **kwargs)
        self.exposure = Param(1., limits=(0.1, 1000), unit="ms", desc="Exposure (ms)")
        self.framerate = Param(
            150., limits=(1, 700), unit=" Hz", desc="Framerate (Hz)"
        )
        self.gain = Param(1., limits=(0.1, 12), desc="Camera amplification gain")
        self.ring_buffer_length = Param(
            300, (1, 2000), desc="Rolling buffer that saves the last items", gui=False
        )
        self.paused = Param(False)
        self.replay = Param(True, desc="Replaying", gui=False)
        self.replay_fps = Param(
            15,
            (0, 500),
            desc="If bigger than 0, the rolling buffer will be replayed at the given framerate",
        )
        self.replay_limits = Param((0, 600), gui=False)
