import numpy as np
from stytra.hardware.video.cameras.interface import Camera

try:
    from pymba import Vimba
    from pymba.vimba_exception import VimbaException
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

    def __init__(self, camera_id=None, **kwargs):
        # Set timeout for frame acquisition. Give this as input?
        self.timeout_ms = 1000
        self.camera_id = camera_id

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
        # Get available cameras:
        camera_ids = self.vimba.camera_ids()
        if self.camera_id is None:
            camera_index = 0
            if len(camera_ids) > 0:
                messages.append(
                    "I:Multiple cameras detected: {}. {} wiil be used.".format(
                        camera_ids, self.camera_id
                    )
                )
        else:
            try:
                camera_index = camera_ids.index(self.camera_id)
            except KeyError:
                raise KeyError(
                    f"Camera id {self.camera_id} is not available (available cameras: {self.camera_ids})"
                )
        messages.append("I:Detected camera {}.".format(camera_ids[camera_index]))
        self.cam = self.vimba.camera(camera_index)

        # Start camera:
        self.cam.open()
        self.frame = self.cam.new_frame()
        self.frame.announce()

        self.cam.start_capture()
        self.frame.queue_for_capture()
        self.cam.run_feature_command("AcquisitionStart")

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
            self.frame.wait_for_capture(self.timeout_ms)
            self.frame.queue_for_capture()
            raw_data = self.frame.buffer_data()
            frame = np.ndarray(
                buffer=raw_data,
                dtype=np.uint8,
                shape=(self.frame.data.height, self.frame.data.width),
            )

        except VimbaException:
            frame = None

        return frame

    def release(self):
        """ """
        self.frame.wait_for_capture(self.timeout_ms)
        self.cam.run_feature_command("AcquisitionStop")
        self.cam.end_capture()
        self.cam.revoke_all_frames()
        self.vimba.shutdown()
