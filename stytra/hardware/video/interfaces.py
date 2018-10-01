from stytra.utilities import HasPyQtGraphParams


class VideoControlParams(HasPyQtGraphParams):
    def __init__(self):
        super().__init__(name="video_params")
        self.add_params(
            framerate={
                "value": 150.,
                "type": "float",
                "limits": (10, 700),
                "suffix": " Hz",
                "tip": "Framerate (Hz)",
            },
            offset=50,
            paused=False,
        )


class CameraControlParameters(HasPyQtGraphParams):
    """HasPyQtGraphParams class for controlling the camera params.
    Ideally, methods to automatically set dynamic boundaries on frame rate and
    exposure time can be implemented. Currently not implemented.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self):
        super().__init__(name="camera_params")
        self.add_params(
            exposure={
                "value": 1.,
                "type": "float",
                "limits": (0.1, 50),
                "suffix": " ms",
                "tip": "Exposure (ms)",
            },
            framerate={
                "value": 150.,
                "type": "float",
                "limits": (10, 700),
                "suffix": " Hz",
                "tip": "Framerate (Hz)",
            },
            gain={
                "value": 1.,
                "type": "float",
                "limits": (0.1, 12),
                "tip": "Camera amplification gain",
            },
        )
