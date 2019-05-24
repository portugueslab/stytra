from stytra.hardware.video.cameras.interface import Camera

try:
    from pypylon import pylon
except ImportError:
    pass


class BaslerCamera(Camera):
    """Class for simple control of a camera such as a webcam using opencv.
    Tested only on a simple USB Logitech 720p webcam. Exposure and framerate
    seem to work.
    Different cameras might have different problems because of the
    camera-agnostic opencv control modules. Moreover, it might not work on a
    macOS because of system-specific problems in the multiprocessing Queues().

    """

    def __init__(self, cam_idx=0, **kwargs):
        super().__init__(**kwargs)
        self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    def open_camera(self):
        """ """
        self.camera.Open()
        self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)

    def set(self, param, val):
        """

        Parameters
        ----------
        param :

        val :


        Returns
        -------

        """
        # pass
        # # try:
        if param == "exposure":
            self.camera.ExposureTime = val
            return ""
        else:
            return param + "not implemented"

    def read(self):
        """ """
        res = self.camera.RetrieveResult(0, pylon.TimeoutHandling_Return)

        return res.Array

    def release(self):
        """ """
        self.camera.stopGrabbing()
