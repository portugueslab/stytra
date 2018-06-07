from stytra.utilities import HasPyQtGraphParams


class CameraControlParameters(HasPyQtGraphParams):
    """
    HasPyQtGraphParams class for controlling the camera params.
    Ideally, methods to automatically set dynamic boundaries on frame rate and
    exposure time can be implemented. Currently not implemented.
    """
    def __init__(self):
        super().__init__(name='tracking_camera_params')
        standard_params_dict = dict(exposure={'value': 1.,
                                              'type': 'float',
                                              'limits': (0.1, 50),
                                              'suffix': ' ms',
                                              'tip': 'Exposure (ms)'},
                                    framerate={'value': 150.,
                                               'type': 'float',
                                               'limits': (10, 700),
                                               'suffix': ' Hz',
                                               'tip': 'Framerate (Hz)'},
                                    gain={'value': 1.,
                                          'type': 'float',
                                          'limits': (0.1, 3),
                                          'tip': 'Camera amplification gain'})

        for key, value in standard_params_dict.items():
            self.add_one_param(key, value)

        self.exp = self.params.param('exposure')
        self.fps = self.params.param('framerate')

        self.exp.sigValueChanged.connect(self.change_fps)
        self.fps.sigValueChanged.connect(self.change_exp)

    def change_fps(self):
        pass
        # self.fps.setValue(1000 / self.exp.value(),blockSignal=self.change_exp)

    def change_exp(self):
        pass
        # self.exp.setValue(1000 / self.fps.value(),blockSignal=self.change_fps)
