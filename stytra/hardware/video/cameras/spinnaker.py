from stytra.hardware.video.cameras.interface import Camera

try:
    import PySpin
except ImportError:
    pass


class SpinnakerCamera(Camera):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system = PySpin.System.GetInstance()
        self.cam = self.system.GetCameras()[0]
        assert isinstance(self.cam, PySpin.CameraPtr)
        self.current_image = None

    def open_camera(self):
        self.cam.Init()
        nodemap = self.cam.GetNodeMap()
        node_acquisition_mode = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(
            node_acquisition_mode
        ):
            print(
                "Unable to set acquisition mode to continuous (enum retrieval). Aborting..."
            )
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
            "Continuous"
        )
        if not PySpin.IsAvailable(
            node_acquisition_mode_continuous
        ) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print(
                "Unable to set acquisition mode to continuous (entry retrieval). Aborting..."
            )
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        self.cam.AcquisitionFrameRateEnable.SetValue(True)
        # self.cam.AcquisitionFrameRate.SetValue(400)

        self.cam.BeginAcquisition()
        return "Spinnaker API camera successfully opened"

    def set(self, param, val):
        """

        Parameters
        ----------
        param :

        val :


        Returns
        -------

        """
        try:
            if param == "exposure":
                # camera wants exposure in us:
                self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                self.cam.ExposureAuto.SetValue(PySpin.GainAuto_Off)
                self.cam.ExposureTime.SetValue(val * 1000)

            if param == "framerate":
                self.cam.AcquisitionFrameRate.SetValue(val)

        except PySpin.SpinnakerException as ex:
            return "Invalid parameters"
        return ""

    def read(self):
        try:
            #  Retrieve next received image
            #
            #  *** NOTES ***
            #  Capturing an image houses images on the camera buffer. Trying
            #  to capture an image that does not exist will hang the camera.
            #
            #  *** LATER ***
            #  Once an image from the buffer is saved and/or no longer
            #  needed, the image must be released in order to keep the
            #  buffer from filling up.
            image_result = self.cam.GetNextImage()

            #  Ensure image completion
            #
            #  *** NOTES ***
            #  Images can easily be checked for completion. This should be
            #  done whenever a complete image is expected or required.
            #  Further, check image status for a little more insight into
            #  why an image is incomplete.
            if image_result.IsIncomplete():
                return

            else:

                #  Print image information; height and width recorded in pixels
                #
                #  *** NOTES ***
                #  Images have quite a bit of available metadata including
                #  things such as CRC, image status, and offset values, to
                #  name a few.
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                #  Convert image to mono 8
                #
                #  *** NOTES ***
                #  Images can be converted between pixel formats by using
                #  the appropriate enumeration value. Unlike the original
                #  image, the converted one does not need to be released as
                #  it does not affect the camera buffer.
                #
                #  When converting images, color processing algorithm is an
                #  optional parameter.
                image_converted = image_result.Convert(
                    PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                )

                # Create a unique filename
                #  Save image
                #
                #  *** NOTES ***
                #  The standard practice of the examples is to use device
                #  serial numbers to keep images of one device from
                #  overwriting those of another.

                #  Release image
                #
                #  *** NOTES ***
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result.Release()
                return image_converted.GetNDArray()

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)
            return None

    def release(self):
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam
        self.system.ReleaseInstance()
