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
            self.camera.ExposureTime = val*1000
            return ""
        # elif param == "framerate":
        #     self.camera.FrameRate = 100
        elif param == "gain":
            self.camera.Gain = val
        else:
            return "W: " + param + " not implemented"

    def read(self):
        """ """
        grabResult = self.camera.RetrieveResult(5000,
                                           pylon.TimeoutHandling_ThrowException)

        if grabResult.GrabSucceeded():
            # Access the image data.
            # print("SizeX: ", grabResult.Width)
            # print("SizeY: ", grabResult.Height)
            img = grabResult.Array
            # print("Gray value of first pixel: ", img[0, 0])
            grabResult.Release()
            return img

        else:
            return None



        # return res.Array

    def release(self):
        """ """
        pass
        # self.camera.stopGrabbing()


if __name__ == "__main__":
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    i = camera.GetNodeMap()

    # camera.Open()
    # camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    # res = camera.RetrieveResult(0, pylon.TimeoutHandling_Return)
    # print(res)
    # re.
    # print(res.Array)
    # camera.stopGrabbing()
    # camera.Close()

    # camera = pylon.InstantCamera(
    #     pylon.TlFactory.GetInstance().CreateFirstDevice())
    camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
    camera.FrameRate = 10

    # while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(5000,
                                       pylon.TimeoutHandling_ThrowException)

    if grabResult.GrabSucceeded():
        # Access the image data.
        print("SizeX: ", grabResult.Width)
        print("SizeY: ", grabResult.Height)
        img = grabResult.Array
        print("Gray value of first pixel: ", img[0, 0])

    grabResult.Release()
