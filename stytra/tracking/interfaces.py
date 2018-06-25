from stytra.utilities import HasPyQtGraphParams


class FrameProcessingMethod(HasPyQtGraphParams):
    """The class for parametrisation of various tail and fish tracking methods"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = dict(image_scale=1.0,
                                    filter_size=0)

        for key in standard_params_dict.keys():
            self.add_one_param(key, standard_params_dict[key])

        self.accumulator_headers = None
        self.data_log_name = None


""" 
Tail tracking methods 
"""


class TailTrackingMethod(FrameProcessingMethod):
    """General tail tracking method."""
    def __init__(self):
        super().__init__(name='tracking_tail_params')
        # TODO maybe getting default values here:
        standard_params_dict = dict(function=dict(values=['centroid',
                                                          'angle_sweep'],
                                                  value='centroid',
                                                  type='list',
                                                  readonly=False),
                                    n_segments=dict(value=10,
                                                    type='int',
                                                    limits=(1, 50)),
                                    color_invert=True,
                                    tail_start=dict(value=(440, 225),
                                                    visible=False),
                                    tail_length=dict(value=(-250, 30),
                                                     visible=False))

        for key, value in standard_params_dict.items():
            self.add_one_param(key, value)

        self.accumulator_headers = ['tail_sum'] + \
                                   ['theta_{:02}'.format(i)
                                    for i in range(self.params['n_segments'])]
        self.data_log_name = 'behaviour_tail_log'


class CentroidTrackingMethod(TailTrackingMethod):
    """Center-of-mass method to find consecutive segments."""
    def __init__(self):
        super().__init__()
        self.params.child('function').setValue('centroid')
        standard_params_dict = dict(window_size=dict(value=30,
                                                     suffix=' pxs',
                                                     type='float',
                                                     limits=(2, 100)))

        for key, value in standard_params_dict.items():
            self.add_one_param(key, value)


class AnglesTrackingMethod(TailTrackingMethod):
    """Angular sweep method to find consecutive segments."""
    def __init__(self):
        super().__init__()
        self.params.child('function').setValue('angle_sweep')


""" 
Eyes tracking methods 
"""


class FishTrackingMethod(FrameProcessingMethod):
    def __init__(self):
        super().__init__(name='tracking_fish_params')
        self.add_params(function='fish',
            threshold=dict(type='int', limits=(0, 255)))

        self.accumulator_headers = ["x", "y", "theta"]
        self.data_log_name = ""


class EyeTrackingMethod(FrameProcessingMethod):
    """General eyes tracking method."""
    def __init__(self):
        super().__init__(name='tracking_tail_params')
        # TODO maybe getting default values here:
        self.add_params(function={'values': ['eye_threshold'],
                                              'value': 'eye_threshold',
                                              'type': 'list',
                                              'readonly': True},
                        color_invert=True,
                        wnd_pos={'value': (140, 200),
                                             'visible': False},
                                    wnd_dim={'value': (110, 60),
                                             'visible': False})

        headers = []
        [headers.extend(['pos_x_e{}'.format(i), 'pos_y_e{}'.format(i),
                         'dim_x_e{}'.format(i), 'dim_y_e{}'.format(i),
                         'th_e{}'.format(i)]) for i in range(2)]
        self.accumulator_headers = headers
        self.data_log_name = 'behaviour_eyes_log'


class ThresholdEyeTrackingMethod(EyeTrackingMethod):
    """Simple threshold method for finding eyes."""
    def __init__(self):
        super().__init__(name='tracking_fish_params')
        standard_params_dict = dict(threshold=dict(value=64,
                                                   type='int',
                                                   limits=(0, 255)))

        for key, value in standard_params_dict.items():
            self.add_one_param(key, value)


class TailEyesTrackingMethod(CentroidTrackingMethod,
                             ThresholdEyeTrackingMethod):
    pass


class MovementDetectionParameters(HasPyQtGraphParams):
    """
    The class for parametrisation of various tail and fish tracking methods
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = dict(fish_threshold=50,
                                    motion_threshold_n_pix=8,
                                    frame_margin=10,
                                    n_previous_save=400,
                                    n_next_save=300,
                                    show_thresholded=False)
        for key in standard_params_dict.keys():
            self.add_one_param(key, standard_params_dict[key])

