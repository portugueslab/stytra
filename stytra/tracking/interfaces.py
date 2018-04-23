from stytra.data_log import HasPyQtGraphParams


class FrameProcessingMethod(HasPyQtGraphParams):
    """ The class for parametrisation of various tail and fish tracking methods
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = dict(image_scale=1.0,
                                    filter_size=0)

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

        self.tracked_variables = []


""" 
Tail tracking methods 
"""


class TailTrackingMethod(FrameProcessingMethod):
    """ General tail tracking method.
    """
    def __init__(self):
        super().__init__(name='tracking_tail_params')
        # TODO maybe getting default values here:
        standard_params_dict = dict(function={'values': ['centroid',
                                                         'angle_sweep'],
                                              'value': 'centroid',
                                              'type': 'list',
                                              'readonly': True},
                                    n_segments=20,
                                    color_invert=True,
                                    tail_start={'value': (440, 225),
                                                'visible': False},
                                    tail_length={'value': (-250, 30),
                                                 'visible': False})

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)


class CentroidTrackingMethod(TailTrackingMethod):
    """ Center-of-mass method to find consecutive segments.
    """
    def __init__(self):
        super().__init__()
        standard_params_dict = dict(window_size=dict(value=30,
                                                     suffix=' pxs',
                                                     type='float',
                                                     limits=(2, 100)))

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)


""" 
Eyes tracking methods 
"""


class EyeTrackingMethod(FrameProcessingMethod):
    """ General eyes tracking method.
    """
    def __init__(self):
        super().__init__(name='tracking_tail_params')
        # TODO maybe getting default values here:
        standard_params_dict = dict(function={'values': ['eye_threshold'],
                                              'value': 'eye_threshold',
                                              'type': 'list',
                                              'readonly': True},
                                    color_invert=True,
                                    wnd_pos={'value': (140, 200),
                                             'visible': False},
                                    wnd_dim={'value': (110, 60),
                                             'visible': False})

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)


class ThresholdEyeTrackingMethod(EyeTrackingMethod):
    """ Simple threshold method for finding eyes.
    """
    def __init__(self):
        super().__init__()
        standard_params_dict = dict(threshold=dict(value=64,
                                                   type='int',
                                                   limits=(0, 255)))

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)


class MovementDetectionParameters(HasPyQtGraphParams):
    """ The class for parametrisation of various tail and fish tracking methods
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = dict(fish_threshold=50,
                                    motion_threshold_n_pix = 8,
                                    frame_margin=10,
                                    n_previous_save=400,
                                    n_next_save=300,
                                    show_thresholded = False)
        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])