import numpy as np
from stytra.hardware.video.cameras.interface import Camera

try:
    from pymba import Vimba
    from pymba.vimbaexception import VimbaException
except ImportError:
    pass


class AvtCamera(Camera):
    """Class for controlling an AVT camera.

    Uses the Vimba interface pymba
    (module documentation `here <https://github.com/morefigs/pymba>`_).

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, **kwargs):
        # Set timeout for frame acquisition. Give this as input?
        self.timeout_ms = 1000

        super().__init__(**kwargs)

        try:
            self.vimba = Vimba()
        except NameError:
            raise Exception("The pymba package must be installed to use an AVT camera!")

        self.frame = None

    def open_camera(self):
        """ """
        self.vimba.startup()
        messages = []
        # If there are multiple cameras, only the first one is used (this may
        # change):
        camera_ids = self.vimba.getCameraIds()
        if len(camera_ids) > 1:
            messages.append(
                "I:Multiple cameras detected: {}. {} wiil be used.".format(
                    camera_ids, camera_ids[0]
                )
            )
        else:
            messages.append("I:Detected camera {}.".format(camera_ids[0]))
        self.cam = self.vimba.getCamera(camera_ids[0])

        # Start camera:
        self.cam.openCamera()
        self.frame = self.cam.getFrame()
        self.frame.announceFrame()

        self.cam.startCapture()
        self.frame.queueFrameCapture()
        self.cam.runFeatureCommand("AcquisitionStart")

        return messages

    def set(self, param, val):
        """

        Parameters
        ----------
        param :

        val :


        Returns
        -------

        """
        messages = []
        try:
            if param == "exposure":
                # camera wants exposure in us:
                self.cam.ExposureTime = int(val * 1000)

            else:
                # To set new frame rate for AVT cameras acquisition has to be
                # interrupted:
                messages.append("E:" + param + " setting not supported on AVT cameras")
        except VimbaException:
            messages.append("E:Invalid value! {} will not be changed.".format(param))
        return messages

    def read(self):
        """ """
        try:
            self.frame.waitFrameCapture(self.timeout_ms)
            self.frame.queueFrameCapture()

            raw_data = self.frame.getBufferByteData()

            frame = np.ndarray(
                buffer=raw_data,
                dtype=np.uint8,
                shape=(self.frame.height, self.frame.width),
            )

        except VimbaException:
            frame = None

        return frame

    def release(self):
        """ """
        self.frame.waitFrameCapture(self.timeout_ms)
        self.cam.runFeatureCommand("AcquisitionStop")
        self.cam.endCapture()
        self.cam.revokeAllFrames()
        self.vimba.shutdown()
