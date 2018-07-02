from stytra.utilities import HasPyQtGraphParams


class MovementDetectionParameters(HasPyQtGraphParams):
    """
    The class for parametrisation of various tail and fish tracking methods
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for child in self.params.children():
            self.params.removeChild(child)

        standard_params_dict = dict(
            fish_threshold=50,
            motion_threshold_n_pix=8,
            frame_margin=10,
            n_previous_save=400,
            n_next_save=300,
            show_thresholded=False,
        )
        for key in standard_params_dict.keys():
            self.add_one_param(key, standard_params_dict[key])
