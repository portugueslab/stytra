import numpy as np
from stytra.hardware.video.cameras.interface import Camera, CameraError

try:
    import PySpin
except ImportError:
    pass


class SpinnakerCamera(Camera):
    """Class for simple control of a Point Grey camera.

    Uses Spinnaker API. Module documentation `here
    <https://www.flir.com/products/spinnaker-sdk/>`_.
    
     Note roi is [x, y, width, height]
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system = PySpin.System.GetInstance()
        self.cam = self.system.GetCameras()[0]
        assert isinstance(self.cam, PySpin.CameraPtr)

    def open_camera(self):
        messages = []
        self.cam.Init()
        nodemap = self.cam.GetNodeMap()

        # SET TO CONTINUOUS ACQUISITION MODE
        acquisition_mode_node = PySpin.CEnumerationPtr(
            nodemap.GetNode("AcquisitionMode")
        )
        if not PySpin.IsAvailable(acquisition_mode_node) or not PySpin.IsWritable(
            acquisition_mode_node
        ):
            messages.append(
                "W: May not be able to set acquisition mode to continuous (enum retrieval)."
            )

        # Retrieve entry node from enumeration node
        acquisition_mode_continuous_node = acquisition_mode_node.GetEntryByName(
            "Continuous"
        )
        if not PySpin.IsAvailable(
            acquisition_mode_continuous_node
        ) or not PySpin.IsReadable(acquisition_mode_continuous_node):
            messages.append(
                "W: Unable to set acquisition mode to continuous (entry retrieval)."
            )
        acquisition_mode_continuous = acquisition_mode_continuous_node.GetValue()
        acquisition_mode_node.SetIntValue(acquisition_mode_continuous)

        # Set ROI first if applicable (framerate limits depend on it)
        try:
            # Note set width/height before x/y offset because upon
            # initialization max offset is 0 because full frame size is assumed
            for i, (s, o) in enumerate(
                zip(["Width", "Height"], ["OffsetX", "OffsetY"])
            ):

                roi_node = PySpin.CIntegerPtr(nodemap.GetNode(s))
                # If no ROI is specified, use full frame:
                if self.roi[2 + i] == -1:
                    value_to_set = roi_node.GetMax()
                else:
                    value_to_set = self.roi[2 + i]
                inc = roi_node.GetInc()
                if np.mod(value_to_set, inc) != 0:
                    value_to_set = (value_to_set // inc) * inc
                    messages.append(
                        "W: Need to set width in increments of {0}, resetting to {1}.".format(
                            inc, value_to_set
                        )
                    )
                roi_node.SetValue(value_to_set)

                # offset
                offset_node = PySpin.CIntegerPtr(nodemap.GetNode(o))
                if self.roi[0 + i] == -1:
                    off_to_set = offset_node.GetMin()
                else:
                    off_to_set = self.roi[0 + i]
                offset_node.SetValue(off_to_set)

        except Exception as ex:
            messages.append("E:Could not set ROI. Exception: {0}.".format(ex))

        # Enabling framerate control from Stytra

        # Disabling auto frame rate
        self.acquisition_rate_node = self.cam.AcquisitionFrameRate
        node_acquisition_frame_rate_control_enable = PySpin.CBooleanPtr(
            nodemap.GetNode("AcquisitionFrameRateEnable")
        )
        if PySpin.IsAvailable(
            node_acquisition_frame_rate_control_enable
        ):  # older simpler api
            self.cam.AcquisitionFrameRateEnable.SetValue(True)
        else:  # newer more complex api
            frame_rate_auto_node = PySpin.CEnumerationPtr(
                nodemap.GetNode("AcquisitionFrameRateAuto")
            )

            node_frame_rate_auto_off = frame_rate_auto_node.GetEntryByName("Off")

            frame_rate_auto_off = node_frame_rate_auto_off.GetValue()
            frame_rate_auto_node.SetIntValue(frame_rate_auto_off)
            enable_rate_mode = PySpin.CBooleanPtr(
                nodemap.GetNode("AcquisitionFrameRateEnabled")
            )
            if not PySpin.IsAvailable(enable_rate_mode) or not PySpin.IsWritable(
                enable_rate_mode
            ):
                messages.append(
                    "W:enable_rate_mode not available/writable. Aborting..."
                )
            try:
                enable_rate_mode.SetValue(True)
            except PySpin.SpinnakerException as ex:
                messages.append("E:Could not enable frame rate: {0}".format(ex))

            # Check to make sure frame rate is now writeable
            if self.acquisition_rate_node.GetAccessMode() != PySpin.RW:
                messages.append("W:Frame rate mode was not set to read&write.")

        # Determine frame rate min/max (this depends on ROI)
        self.rate_max = self.acquisition_rate_node.GetMax()
        self.rate_min = self.acquisition_rate_node.GetMin()

        # Making exposure controllable
        # Turn off auto exposure
        exposure_auto_node = self.cam.ExposureAuto
        if exposure_auto_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Unable to disable automatic exposure. Aborting...")
        exposure_auto_node.SetValue(PySpin.ExposureAuto_Off)
        # Check for availability/writeability of exposure time
        self.exposure_time_node = self.cam.ExposureTime
        if self.exposure_time_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Exposure time is not read/write")
        self.exposure_max = self.exposure_time_node.GetMax()
        self.exposure_min = self.exposure_time_node.GetMin()

        # Making gain controllable
        # Turn off auto-gain
        gain_auto_node = self.cam.GainAuto
        if gain_auto_node.GetAccessMode() != PySpin.RW:
            messages.append("W:Unable to disable automatic gain.")
        gain_auto_node.SetValue(PySpin.GainAuto_Off)
        self.gain_node = self.cam.Gain
        self.gain_min = self.gain_node.GetMin()
        self.gain_max = self.gain_node.GetMax()

        # Starting acquisition
        self.cam.BeginAcquisition()
        messages.append("I:Opened Point Grey camera")
        return messages

    def set(self, param, val):
        """

        Parameters
        ----------
        param : string name
        val : value in appropriate format for parameter
        Returns string
        -------

        """
        messages = []
        try:
            if param == "exposure":  # sent in ms
                # camera wants exposure in us:
                exposure_time_to_set = val * 1000  # convert to microseconds
                if exposure_time_to_set > self.exposure_max:
                    messages.append(
                        "E:exposure greater than max of {:3.1f}".format(
                            self.exposure_max / 1000
                        )
                    )
                    exposure_time_to_set = self.exposure_max
                elif exposure_time_to_set < self.exposure_min:
                    messages.append(
                        "E:exposure less than min of {:3.1f}".format(
                            self.exposure_min / 1000
                        )
                    )
                    exposure_time_to_set = self.exposure_min
                self.exposure_time_node.SetValue(exposure_time_to_set)

            if param == "gain":
                gain_to_set = val
                if gain_to_set > self.gain_max:
                    messages.append(
                        "E:gain greater than max of {:3.1f}".format(self.gain_max)
                    )
                    gain_to_set = self.gain_max
                elif gain_to_set < self.gain_min:
                    messages.append(
                        "E:gain less than min of {:3.1f}".format(self.gain_min)
                    )
                    gain_to_set = self.gain_min
                if self.gain_node.GetAccessMode() != PySpin.RW:
                    messages.append("E:gain is not r/w - another camera window open?")
                self.gain_node.SetValue(gain_to_set)

            if param == "framerate":
                frame_rate = val
                if frame_rate > self.rate_max:
                    messages.append(
                        "E:fps greater than max of {:3.1f}".format(self.rate_max)
                    )
                    frame_rate = self.rate_max
                elif frame_rate < self.rate_min:
                    messages.append(
                        "E:fps less than min of {:3.1f}".format(self.rate_min)
                    )
                    frame_rate = self.rate_min
                self.acquisition_rate_node.SetValue(frame_rate)

        except PySpin.SpinnakerException as ex:
            err = "E: SpinnakerCamera.set() error: {0}".format(ex)
            messages.append(err)
            # return err
        return messages

    def read(self):
        try:
            #  Retrieve next received image
            image_result = self.cam.GetNextImage()

            #  Ensure image completion
            if image_result.IsIncomplete():
                return

            else:
                image_converted = np.array(
                    image_result.GetData(), dtype="uint8"
                ).reshape((image_result.GetHeight(), image_result.GetWidth()))
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result.Release()
                return image_converted

        except PySpin.SpinnakerException as ex:
            raise CameraError("Frame not read")

    def release(self):
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam
        self.system.ReleaseInstance()
