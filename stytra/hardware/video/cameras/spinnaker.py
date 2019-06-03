import numpy as np  
from stytra.hardware.video.cameras.interface import Camera

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
        self.cam.Init()
        nodemap = self.cam.GetNodeMap()
        
        # SET TO CONTINUOUS ACQUISITION MODE
        acquisition_mode_node = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        if not PySpin.IsAvailable(acquisition_mode_node) or not PySpin.IsWritable(acquisition_mode_node):
            print("W: May not be able to set acquisition mode to continuous (enum retrieval).")

        # Retrieve entry node from enumeration node
        acquisition_mode_continuous_node = acquisition_mode_node.GetEntryByName("Continuous")
        if not PySpin.IsAvailable(acquisition_mode_continuous_node) or not PySpin.IsReadable(acquisition_mode_continuous_node):
            print('W: Unable to set acquisition mode to continuous (entry retrieval).')
        acquisition_mode_continuous = acquisition_mode_continuous_node.GetValue()
        acquisition_mode_node.SetIntValue(acquisition_mode_continuous)
        print ("I: Acquisition Mode successfully set to Continuous...")

        # SET ROI, IF APPLICABLE
        #Set first as frame rate limits depend on this
        if self.roi[0] > 0:
            try:
                #Width (set width/height before x,y b/c initially max x,y offset is 0)
                width_node = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
                if PySpin.IsAvailable(width_node) and PySpin.IsWritable(width_node):
                    #width_to_set = width_node.GetMax()    #default
                    width_inc = width_node.GetInc()
                    width_to_set = self.roi[2]
                    if np.mod(width_to_set, width_inc) != 0:
                        width_to_set = (width_to_set//width_inc)*width_inc
                        print("W: Need to set width in increments of {0}, resetting to {1}.".format(width_inc, width_to_set))
                    try:
                        width_node.SetValue(width_to_set)
                    except PySpin.SpinnakerException as ex:
                        print("E: Could not set width: {0}".format(ex))
                    else:
                        print("I: Width set to {0}.".format(width_node.GetValue()))           
                else:
                    print("W: ROI width not available...")
                    
                # Height
                height_node = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
                if PySpin.IsAvailable(height_node) and PySpin.IsWritable(height_node):
                    #height_to_set = height_node.GetMax()  #default
                    height_inc = height_node.GetInc()
                    height_to_set = self.roi[3]
                    if np.mod(height_to_set, height_inc) != 0:
                        height_to_set = (height_to_set//height_inc)*height_inc
                        print("W: Need to set height in increments of {0}, resetting to {1}.".format(height_inc, height_to_set))
                    try:
                        height_node.SetValue(height_to_set)
                    except PySpin.SpinnakerException as ex:
                        print("E: Could not set height: {0}".format(ex))
                    else:
                        print("I: Height set to {0}".format(height_node.GetValue()))
                else:
                    print("W: ROI height not available...")   

                
                # x-offset
                offset_x_node = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
                if PySpin.IsAvailable(offset_x_node) and PySpin.IsWritable(offset_x_node):
                    x_to_set = self.roi[0]  #offset_x_node.GetMin() is default
                    try:
                        offset_x_node.SetValue(x_to_set)
                    except PySpin.SpinnakerException as ex:
                        print("E: Could not set x-offset: {0}".format(ex))
                    else:
                        print("I: x offset set to {0}".format(offset_x_node.GetValue()))
                else:
                    print("W: ROI x-offset not available...")
                
                # y-offset
                offset_y_node = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
                if PySpin.IsAvailable(offset_y_node) and PySpin.IsWritable(offset_y_node):
                    #y_to_set = offset_y_node.GetMin()  #default (usually 0)
                    #print("    Min, max y: ", offset_y_node.GetMin(), offset_y_node.GetMax())
                    y_to_set = self.roi[1]
                    try:
                        offset_y_node.SetValue(y_to_set)
                    except PySpin.SpinnakerException as ex:
                        print("E: Could not set y-offset: {0}".format(ex))
                    else:
                        print("I: y offset set to {0}".format(offset_y_node.GetValue()))
                else:
                    print("W: ROI y-offset not available...")
                    return False
                print("I: ROI successfully enabled")
            except Exception as ex:
                print("E: Could not set ROI. Exeption: ", str(ex))
               
        # ENABLE FRAME RATE (set before exposure as exposure limits depend on this)
        # First, disable auto frame rate
        self.acquisition_rate_node = self.cam.AcquisitionFrameRate
        node_acquisition_frame_rate_control_enable = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
        if PySpin.IsAvailable(node_acquisition_frame_rate_control_enable): #older simpler api
            self.cam.AcquisitionFrameRateEnable.SetValue(True)
            print("I:Successfully enabled frame rate using legacy node")
        else:  #newer more complex api
            frame_rate_auto_node = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionFrameRateAuto"))
            if not PySpin.IsAvailable(frame_rate_auto_node) or not PySpin.IsWritable(frame_rate_auto_node):
                print ("W: Unable to retrieve frame rate auto node.")    
            node_frame_rate_auto_off = frame_rate_auto_node.GetEntryByName("Off")
            if not PySpin.IsAvailable(node_frame_rate_auto_off) or not PySpin.IsReadable(node_frame_rate_auto_off):
                print ("W: frame rate auto may not be available.")
            frame_rate_auto_off = node_frame_rate_auto_off.GetValue()
            frame_rate_auto_node.SetIntValue(frame_rate_auto_off)     
            print( "I: Frame Rate Auto set to Off...")
            # Enable frame rate control
            enable_rate_mode = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnabled"))
            if not PySpin.IsAvailable(enable_rate_mode) or not PySpin.IsWritable(enable_rate_mode):
                print("W:  enable_rate_mode not available/writable. Aborting...")
            try:
                enable_rate_mode.SetValue(True)
            except PySpin.SpinnakerException as ex:
                print("E: Could not enable frame rate: {0}".format(ex))
            # Check to make sure you successfully made frame rate writeable
            if self.acquisition_rate_node.GetAccessMode() != PySpin.RW:  
                print("W: Frame rate mode was not set to read/write.")
            else:
                print("I: Frame rate successfully enabled.")
        #Determine frame rate min/max (this depends on ROI)
        self.rate_max = self.acquisition_rate_node.GetMax()
        self.rate_min = self.acquisition_rate_node.GetMin()
        print("I: Frame rate min/max: ", self.rate_min, '/', self.rate_max)   
            
        # ENABLE SETTING EXPOSURE 
        #Turn off auto exposure
        exposure_auto_node = self.cam.ExposureAuto
        if exposure_auto_node.GetAccessMode() != PySpin.RW:
            print('W: Unable to disable automatic exposure. Aborting...')
        exposure_auto_node.SetValue(PySpin.ExposureAuto_Off)       
        # Check for availability/writeability of exposure time
        self.exposure_time_node = self.cam.ExposureTime
        if self.exposure_time_node.GetAccessMode() != PySpin.RW:
            print('W: Exposure time is not read/write')
        self.exposure_max = self.exposure_time_node.GetMax()
        self.exposure_min = self.exposure_time_node.GetMin()
        print("I: min/max exposure time (ms): ", self.exposure_min/1000, '/', self.exposure_max/1000)
        print("I: Exposure successfully enabled.")
        
        
        # ENABLE SETTING GAIN (default 0)
        #Turn off auto-gain
        gain_auto_node = self.cam.GainAuto
        if gain_auto_node.GetAccessMode() != PySpin.RW:
            print('W: Unable to disable automatic gain.')
        gain_auto_node.SetValue(PySpin.GainAuto_Off)
        self.gain_node = self.cam.Gain
        self.gain_min = self.gain_node.GetMin()
        self.gain_max = self.gain_node.GetMax()
        print("I: Gain successfully enabled\n")

        #  START ACQUISITION
        self.cam.BeginAcquisition()
        return "I: Opened Point Grey camera"

    def set(self, param, val):
        """

        Parameters
        ----------
        param : string name
        val : value in appropriate format for parameter
        Returns string
        -------

        """
        try:
            if param == "exposure":  #sent in ms
                # camera wants exposure in us:
                exposure_time_to_set = val*1000  #convert to microseconds
                if exposure_time_to_set > self.exposure_max:
                    print("W: exposure time greater than max: setting it to max of ", self.exposure_max/1000)
                    exposure_time_to_set = self.exposure_max
                elif exposure_time_to_set < self.exposure_min:
                    print("W: exposure time less than min: setting it to min of ", self.exposure_min/1000)
                    exposure_time_to_set = self.exposure_min
                self.exposure_time_node.SetValue(exposure_time_to_set)
                print("I: Exposure sucessfully set to ", exposure_time_to_set/1000, " ms")

            if param == "gain":
                gain_to_set = val
                if gain_to_set > self.gain_max:
                    print("W: gain greater than max - setting it to max of ", self.gain_max)
                    gain_to_set = self.gain_max
                elif gain_to_set < self.gain_min:
                    print("W: gain less than min - setting it to min of ", self.gain_min)
                    gain_to_set = self.gain_min
                if self.gain_node.GetAccessMode() != PySpin.RW:
                    print("W. gain doesn't seem to be read/write -- do you have SpinView or another camera window open?")
                self.gain_node.SetValue(gain_to_set)
                print("I: Gain successfully set to {0}.".format(gain_to_set))

            if param == "framerate":
                frame_rate = val
                if frame_rate > self.rate_max:
                    print("W: attempt to set fps greater than max, setting to ", self.rate_max)
                    frame_rate = self.rate_max
                elif frame_rate < self.rate_min:
                    print("W: attempt to set fps less than min, setting to ", self.rate_min)
                    frame_rate = self.rate_min
                self.acquisition_rate_node.SetValue(frame_rate)  
                print("I: Frame rate successfully set to ", frame_rate, " hz")
    

        except PySpin.SpinnakerException as ex:
            err = "E: SpinnakerCamera.set() error: {0}".format(ex)
            print(err)
            return err
        return ""

    def read(self):
        try:
            #  Retrieve next received image
            image_result = self.cam.GetNextImage()

            #  Ensure image completion
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
            print("E: {0}".format(ex))
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
    frame_rate = 3.0
    roi_test = [500, 200, 640, 320]  #x, y, width, height
    print("\n**Testing SpinnakerCamera()**".format(frame_rate))
    import cv2
    cv2.namedWindow("StytraSpin", cv2.WINDOW_NORMAL)
    spinCam = SpinnakerCamera(roi = roi_test)
    spinCam.open_camera()
    spinCam.set("framerate", frame_rate)
    spinCam.set("gain", 1.)
    spinCam.set("exposure", 15.)
    while True:
        image = spinCam.read()
        cv2.imshow("StytraSpin", image)
        key = cv2.waitKey(1)  
        if key == 27: #escape key
            print("I: Streaming stopped")
            cv2.destroyAllWindows()
            spinCam.release()
            break