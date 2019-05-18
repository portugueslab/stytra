import numpy as np  
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
        
        ### Enable frame rate control
        enable_rate_control = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnabled"))
        if not PySpin.IsAvailable(
                enable_rate_control
        ) or not PySpin.IsWritable(enable_rate_control):
            print("enable_rate_control not writable. Aborting...")
            return False
        enable_rate_control.SetValue(True)
        if self.cam.AcquisitionFrameRate.GetAccessMode() != PySpin.RW:  
            print("Frame rate mode not set to read/write. Aborting...")
            return False
        #To test frame rate control
        #frame_rate = 1.0; self.cam.AcquisitionFrameRate.SetValue(frame_rate)       

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
            return "Invalid parameters" + ex
        return ""

    def read(self):
        try:
            #  Retrieve next received image
            #
            #  Capturing an image houses images on the camera buffer. Trying
            #  to capture an image that does not exist will hang the camera.
            image_result = self.cam.GetNextImage()

            #  Ensure image completion
            #
            #  Images can easily be checked for completion. This should be
            #  done whenever a complete image is expected or required.
            #  Further, check image status for a little more insight into
            #  why an image is incomplete.
            if image_result.IsIncomplete():
                return

            else:
                image_converted = np.array(image_result.GetData(), dtype="uint8").reshape((image_result.GetHeight(), 
                                                                                           image_result.GetWidth()) );
                #  Images retrieved directly from the camera (i.e. non-converted
                #  images) need to be released in order to keep from filling the
                #  buffer.
                image_result.Release()
                return image_converted
            
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)
            return None

    def release(self):
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam
        self.system.ReleaseInstance()

if __name__ == "__main__":
    """ 
    Test PySpin api/SpinnakerCamera() using opencv.
    """
    print("\n**Testing SpinnakerCamera(): displaying data at 1Hz**")
    import cv2
    cv2.namedWindow("Stytra Spinnaker Stream", cv2.WINDOW_NORMAL)
    spinCam = SpinnakerCamera()
    spinCam.open_camera()
    spinCam.set("framerate", 1.0)
    while True:
        image = spinCam.read()
        cv2.imshow("Stytra Spinnaker Stream", image)
        key = cv2.waitKey(1)  
        if key == 27: #escape key
            print("Streaming stopped")
            cv2.destroyAllWindows()
            spinCam.release()
            break