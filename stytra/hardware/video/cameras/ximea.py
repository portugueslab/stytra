from stytra.hardware.video.cameras.interface import Camera

try:
    from ximea import xiapi
except ImportError:
    pass


class XimeaCamera(Camera):
    """Class for simple control of a Ximea camera.

    Uses ximea API. Module documentation `here
    <https://www.ximea.com/support/wiki/apis/Python>`_.

    """

    def __init__(self, **kwargs):
        """

        Parameters
        ----------
        downsampling : int
            downsampling factor for the camera
        """
        super().__init__(**kwargs)

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

        # If camera supports hardware downsampling (MQ013MG-ON does,
        # MQ003MG-CM does not):
        if self.cam.get_device_name() == b"MQ013MG-ON":
            self.cam.set_sensor_feature_selector("XI_SENSOR_FEATURE_ZEROROT_ENABLE")
            self.cam.set_sensor_feature_value(1)


            self.cam.set_downsampling_type("XI_SKIPPING")
            self.cam.set_downsampling(
                "XI_DWN_{}x{}".format(self.downsampling, self.downsampling)
            )

        try:
            if self.roi[0] >= 0:
                self.cam.set_width(self.roi[2])
                self.cam.set_height(self.roi[3])
                self.cam.set_offsetX(self.roi[0])
                self.cam.set_offsetY(self.roi[1])
        except xiapi.Xi_error:
            return ("E:Could not set ROI "+str(self.roi)+", w has to be {}:{}:{}".format(
                self.cam.get_width_minimum(),
                self.cam.get_width_increment(),
                self.cam.get_width_maximum()
            ) + ", h has to be {}:{}:{}".format(
                self.cam.get_height_minimum(),
                self.cam.get_height_increment(),
                self.cam.get_height_maximum()))

        self.cam.start_acquisition()
        self.cam.set_acq_timing_mode("XI_ACQ_TIMING_MODE_FRAME_RATE")
        return "I:Opened Ximea camera " + str(self.cam.get_device_name())

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
            return "Invalid camera parameters"

    def read(self):
        """ """
        try:
            self.cam.get_image(self.im)
            frame = self.im.get_image_data_numpy()
        except xiapi.Xi_error:
            frame = None

        return frame

    def release(self):
        """ """
        self.cam.stop_acquisition()
        self.cam.close_device()
