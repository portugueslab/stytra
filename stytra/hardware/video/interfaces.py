from lightparam.param_qt import ParametrizedQt, Param


class VideoControlParameters(ParametrizedQt):
    def __init__(self, **kwargs):
        super().__init__(name="video_params", **kwargs)
        self.framerate = Param(150., limits=(10, 700),
                               unit="Hz", desc="Framerate (Hz)")
        self.offset = Param(50)
        self.paused = Param(False)


class CameraControlParameters(ParametrizedQt):
    """HasPyQtGraphParams class for controlling the camera params.
    Ideally, methods to automatically set dynamic boundaries on frame rate and
    exposure time can be implemented. Currently not implemented.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, **kwargs):
        super().__init__(name="camera_params", **kwargs)
        self.exposure = Param(1., limits=(0.1, 50), unit="ms",
                              desc="Exposure (ms)")
        self.framerate = Param(150., limits=(10, 700), unit=" Hz",
                              desc="Framerate (Hz)")
        self.gain = Param(1., limits=(0.1, 12),
                              desc="Camera amplification gain")