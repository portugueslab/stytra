# -*- coding: utf-8 -*-
"""
    Authors:
    Vilim Stih
    Andreas Kist
    Luigi Petrucco
"""
"""
This module implement classes that can be used in stytra to control cameras.
"""
import numpy as np

# XIMEA
try:
    from ximea import xiapi
except ImportError:
    pass

# AVT/Vimba
try:
    from pymba import Vimba
    from pymba.vimbaexception import VimbaException
except ImportError:
    pass

# PointGray/FLIR
try:
    import PySpin
except ImportError:
    pass

import ctypes
import logging
import multiprocessing_logging


class Camera:
    """Abstract class for controlling a camera.

    Subclasses implement minimal
    control over the following cameras:
     - Ximea (uses ximea python API `xiAPI <https://www.ximea.com/support/wiki/apis/Python>`_;
     - AVT   (uses `pymba <https://github.com/morefigs/pymba>`_,
       a python wrapper for AVT Vimba package).

    Examples
    --------
    Simple usage of a camera class::

        cam = AvtCamera()
        cam.open_camera()  # initialize the camera
        cam.set('exposure', 10)  # set exposure time in ms
        frame = cam.read()  # read frame
        cam.release()  # close the camera


    Attributes
    ----------
    cam :
        camera object (class depends on camera type).

    debug : bool
        if true, state of the camera is printed.


    """

    def __init__(self, debug=False, **kwargs):
        """
        Parameters
        ----------
        debug : str
            if True, info about the camera state will be printed.
        """
        self.cam = None
        self.debug = debug
        self.error_log = logging.getLogger()
        multiprocessing_logging.install_mp_handler(self.error_log)

    def open_camera(self):
        """Initialise the camera."""

    def set(self, param, val):
        """Set exposure time or the framerate to the camera.

        Parameters
        ----------
        param : str
            parameter key ('exposure', 'framerate'));
        val :
            value to be set (exposure time in ms, or framerate in Hz);

        """
        pass

    def read(self):
        """Grab frame from the camera and returns it as an NxM numpy array.

        Returns
        -------
        np.array
                the grabbed frame, or None if an error occurred.

        """
        return None

    def release(self):
        """Close the camera.
        """
        pass


class XimeaCamera(Camera):
    """Class for simple control of a Ximea camera.

    Uses ximea API. Module documentation `here
    <https://www.ximea.com/support/wiki/apis/Python>`_.

    """

    def __init__(self, downsampling=1, **kwargs):
        """

        Parameters
        ----------
        downsampling : int
            downsampling factor for the camera
        """
        super().__init__(**kwargs)
        self.downsampling = downsampling

        # Test if API for the camera is available
        try:
            self.cam = xiapi.Camera()
        except NameError:
            raise Exception(
                "The xiapi package must be installed to use a Ximea camera!"
            )

    def open_camera(self):
        """ """
        self.cam.open_device()

        self.im = xiapi.Image()
        self.cam.start_acquisition()

        self.error_log.info("Detected camera {}.".format(self.cam.get_device_name()))

        # If camera supports hardware downsampling (MQ013MG-ON does,
        # MQ003MG-CM does not):
        if self.cam.get_device_name() == b"MQ013MG-ON":
            self.cam.set_sensor_feature_selector("XI_SENSOR_FEATURE_ZEROROT_ENABLE")
            self.cam.set_sensor_feature_value(1)

            if self.downsampling > 1:
                self.cam.set_downsampling_type("XI_SKIPPING")
                self.cam.set_downsampling(
                    "XI_DWN_{}x{}".format(self.downsampling, self.downsampling)
                )

        self.cam.set_acq_timing_mode("XI_ACQ_TIMING_MODE_FRAME_RATE")
        self.cam.set_framerate(100.0)

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
                self.cam.set_exposure(int(val * 1000))

            if param == "framerate":
                self.cam.set_framerate(val)
        except xiapi.Xi_error:
            print("Invalid camera parameters")

    def read(self):
        """ """
        try:
            self.cam.get_image(self.im)
            frame = self.im.get_image_data_numpy()
        except xiapi.Xi_error:
            frame = None
            if self.debug:
                print("Unable to acquire frame")

        return frame

    def release(self):
        """ """
        self.cam.stop_acquisition()
        self.cam.close_device()


class AvtCamera(Camera):
    """Class for controlling an AVT camera.

    Uses the Vimba interface pymba
    (module documentation `here <https://github.com/morefigs/pymba>`_).

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, downsampling=None, **kwargs):
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

        # If there are multiple cameras, only the first one is used (this may
        # change):
        camera_ids = self.vimba.getCameraIds()
        if self.debug:
            if len(camera_ids) > 1:
                print(
                    "Multiple cameras detected: {}. {} wiil be used.".format(
                        camera_ids, camera_ids[0]
                    )
                )
            else:
                print("Detected camera {}.".format(camera_ids[0]))
        self.cam = self.vimba.getCamera(camera_ids[0])

        # Start camera:
        self.cam.openCamera()
        self.frame = self.cam.getFrame()
        self.frame.announceFrame()

        self.cam.startCapture()
        self.frame.queueFrameCapture()
        self.cam.runFeatureCommand("AcquisitionStart")

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
                self.cam.ExposureTime = int(val * 1000)

            if param == "framerate":
                # To set new frame rate for AVT cameras acquisition has to be
                # interrupted:
                pass
        except VimbaException:
            print("Invalid value! The parameter will not be changed.")

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
            if self.debug:
                print("Unable to acquire frame")

        return frame

    def release(self):
        """ """
        self.frame.waitFrameCapture(self.timeout_ms)
        self.cam.runFeatureCommand("AcquisitionStop")
        self.cam.endCapture()
        self.cam.revokeAllFrames()
        self.vimba.shutdown()


class SpinnakerCamera(Camera):
    def __init__(self, *args, **kwargs):
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
        self.cam.AcquisitionFrameRate.SetValue(400)

        self.cam.BeginAcquisition()

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
            print("Error: %s" % ex)
        pass

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


class IMAQCamera(Camera):
    def __init__(self, *args, camera_id="img0", **kwargs):
        super().__init__(*args, **kwargs)
        self.cam_id = ctypes.c_char_p(bytes(camera_id, "ansi"))
        self.interface_id = ctypes.c_uint32()
        self.session_id = ctypes.c_uint32()
        self.w, self.h = ctypes.c_uint32(), ctypes.c_uint32()
        self.b_per_px = ctypes.c_uint32()
        self.img_buffer = None
        self.buffer_address = None
        try:
            self.imaq = ctypes.windll.imaq
        except OSError:
            print("NI Vision drivers not installed")

    def open_camera(self):
        int_opened = self.imaq.imgInterfaceOpen(
            self.cam_id, ctypes.byref(self.interface_id)
        )
        session_opened = self.imaq.imgSessionOpen(
            self.interface_id, ctypes.byref(self.session_id)
        )
        self.imaq.imgGrabSetup(self.session_id, 1)

        attr_base = 0x3FF60000

        attr_h = 0x01A7
        attr_w = 0x01A6
        attr_bytes_px = 0x0067

        for atr, var in zip(
            [attr_h, attr_w, attr_bytes_px], [self.h, self.w, self.b_per_px]
        ):
            self.imaq.imgGetAttribute(
                self.session_id, ctypes.c_uint32(attr_base + atr), ctypes.byref(var)
            )

        self.img_buffer = np.ndarray(
            shape=(self.h.value, self.w.value), dtype=ctypes.c_uint8
        )
        self.buffer_address = self.img_buffer.ctypes.data_as(
            ctypes.POINTER(ctypes.c_long)
        )

    def set(self, param, val):
        attr_base = 0x3FF60000
        attr_exposure = ctypes.c_uint32(attr_base + 0x01C0)
        attr_framerate = ctypes.c_uint32(attr_base + 0x01C1)

        ret = -100
        if param == "exposure":
            # camera wants exposure in ms:
            ret = self.imaq.imgSetAttribute2(
                self.session_id, attr_exposure, ctypes.c_uint32(int(val))
            )

        if param == "framerate":
            ret = self.imaq.imgSetAttribute2(
                self.session_id, attr_framerate, ctypes.c_uint32(int(val))
            )
        print(param, val, ret)

    def read(self):
        err = self.imaq.imgGrab(self.session_id, ctypes.byref(self.buffer_address), 1)
        return self.img_buffer

    def release(self):
        self.imaq.imgSessionStopAcquisition(self.session_id)
        self.imaq.imgClose(self.session_id, True)
        self.imaq.imgClose(self.interface_id, True)
