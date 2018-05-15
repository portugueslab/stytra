"""
Module to interact with video surces as cameras or video files. It also
implement video saving
"""

import numpy as np
import glob

from multiprocessing import Queue, Event
from multiprocessing.queues import Empty, Full
from arrayqueues.processes import FrameProcessor
from arrayqueues.shared_arrays import TimestampedArrayQueue

from stytra.hardware.video.cameras import XimeaCamera, AvtCamera
from stytra.hardware.video.write import VideoWriter
from stytra.hardware.video.interfaces import CameraControlParameters


class VideoSource(FrameProcessor):
    """
    Abstract class for a process that generates frames, being it a camera
    or a file source. A maximum size of the memory used by the process can be
    set.

    ===================== ===================================================
    **Input Queues:**
    self.control_queue    queue with control parameters for the source,
                          e.g. from a
                          :class:CameraControlParameters
                          <.interfaces.CameraControlParameters> object
    ===================== ===================================================

    ===================== ===================================================
    **Output Queues**
    self.frame_queue      TimestampedArrayQueue from the arrayqueues module
                          where the frames read from the camera are sent.
    ===================== ===================================================

    ===================== ===================================================
    **Events**
    self.kill_signal      When set kill the process.
    ===================== ===================================================

    """
    def __init__(self, rotation=False, max_mbytes_queue=100):
        """
        :param rotation: if true, rotate image by 90 degrees;
        :param max_mbytes_queue:
        """
        super().__init__()
        self.rotation = rotation
        self.control_queue = Queue()
        self.frame_queue = TimestampedArrayQueue(max_mbytes=max_mbytes_queue)
        self.kill_signal = Event()


class CameraSource(VideoSource):
    """
    Process for controlling a camera.
    Cameras currently implemented:

    Module documentation here_:

    .. _here: <https://www.ximea.com/support/wiki/apis/Python>_

    ======== ===========================================
    Ximea    Add some info
    Avt      Add some info
    ======== ===========================================
    """

    camera_class_dict = dict(ximea=XimeaCamera,
                             avt=AvtCamera)

    def __init__(self, camera_type, *args, **kwargs):
        """
        :param camera_type: string indicating camera type ('ximea' or 'avt')
        """
        super().__init__(*args, **kwargs)

        self.camera_type = camera_type
        self.cam = None

    def run(self):
        """
        This process constantly try to read frames from the camera and to get
        parameters from the parameter queue to update the camera params.
        """
        try:
            CameraClass = self.camera_class_dict[self.camera_type]
            self.cam = CameraClass(debug=True)
        except KeyError:
            print('{} is not a valid camera type!'.format(self.camera_type))
        self.cam.open_camera()
        while True:
            # Kill if signal is set:
            self.kill_signal.wait(0.0001)
            if self.kill_signal.is_set():
                break

            # Try to get new parameters from the control queue:
            if self.control_queue is not None:
                try:
                    param, value = self.control_queue.get(timeout=0.0001)
                    self.cam.set(param, value)
                except Empty:
                    pass

            # Grab the new frame, and put it in the queue if valid:
            arr = self.cam.read()
            if arr is not None:
                # If the queue is full, arrayqueues should print a warning!
                if self.rotation:
                    arr = np.rot90(arr, self.rotation)
                self.frame_queue.put(arr)

        self.cam.release()


class VideoFileSource(VideoSource):
    """
    A class to stream videos from a file to test parts of
    stytra without a camera available.
    """
    def __init__(self, source_file=None,
                 loop=True, framerate=300,
                 **kwargs):
        super().__init__(**kwargs)
        self.source_file = source_file
        self.loop = loop

    def run(self):
        # If the file is a Ximea Camera sequence, frames in the  corresponding
        # folder are read.
        import cv2
        im_sequence_flag = self.source_file.split('.')[-1] == 'xiseq'
        if im_sequence_flag:
            frames_fn = glob.glob('{}_files/*'.format(self.source_file.split('.')[-2]))
            frames_fn.sort()
            k = 0
        else:
            cap = cv2.VideoCapture(self.source_file)
        ret = True

        while ret and not self.kill_signal.is_set():
            if self.source_file.split('.')[-1] == 'xiseq':
                frame = cv2.imread(frames_fn[k])
                k += 1
                if k == len(frames_fn) - 2:
                    ret = False
            else:
                ret, frame = cap.read()

            if ret:
                self.frame_queue.put(frame[:, :, 0])
            else:
                if self.loop:
                    if im_sequence_flag:
                        k = 0
                    else:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret = True
                else:
                    break
            self.update_framerate()
        return

if __name__=='__main__':
    process = CameraSource('ximea')
    process.start()
    process.kill_signal.set()
