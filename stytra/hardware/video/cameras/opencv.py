from stytra.hardware.video.cameras.interface import Camera
import cv2
import numpy as np


class OpenCVCamera(Camera):
    """Class for simple control of a camera such as a webcam using opencv.
    Tested only on a simple USB Logitech 720p webcam. Exposure and framerate
    seem to work.
    Different cameras might have different problems because of the
    camera-agnostic opencv control modules. Moreover, it might not work on a
    macOS because of system-specific problems in the multiprocessing Queues().

    """

    def __init__(self, cam_idx=0, bw=False, **kwargs):
        """

        Parameters
        ----------
        downsampling : int
            downsampling factor for the camera
        """
        super().__init__(**kwargs)

        # Test if API for the camera is available
        self.cam = cv2.VideoCapture(cam_idx)
        self.bw = bw

    def open_camera(self):
        """ """
        return "Webcam opened!"

    def set(self, param, val):
        if param == "exposure":
            self.cam.set(cv2.CAP_PROP_EXPOSURE, val)
        #
        if param == "framerate":
            self.cam.set(cv2.CAP_PROP_FPS, val)

    def read(self):
        """ """
        try:
            ret, frame = self.cam.read()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except cv2.error:
            raise cv2.error("OpenCV can't find a camera!")
        if self.bw:
            return np.mean(rgb, 2).astype(rgb.dtype)
        else:
            return rgb

    def release(self):
        """ """
        self.cam.release()
