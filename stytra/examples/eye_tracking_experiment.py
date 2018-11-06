import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import MovingWindmillStimulus, MovingGratingStimulus
from lightparam import Param


class MixedProtocol(Protocol):
    name = "windmill_gratings"

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(2.)
        self.theta_amp = Param(np.pi / 2)
        self.windmill_freq = Param(0.2)
        self.grating_vel = Param(10)
        self.stim_duration = Param(5.)
        self.wave_shape = Param(value="square",
                                limits=["square", "sinusoidal"])
        self.n_arms = Param(10)

    def get_stim_sequence(self):
        stimuli = []
        p = self.inter_stim_pause / 2
        d = self.stim_duration

        # Windmill
        STEPS = 0.005
        t = np.arange(0, d, STEPS)
        theta = (
            np.sin(2 * np.pi * t * self.windmill_freq)
            * self.theta_amp
        )

        t = [t[0]] + list(t + p) + [(t + 2 * p)[-1]]
        theta = [theta[0]] + list(theta) + [theta[-1]]
        df = pd.DataFrame(dict(t=t, theta=theta))
        stimuli.append(MovingWindmillStimulus(df_param=df))
        return stimuli


if __name__ == "__main__":
    # save_dir = tempfile.mkdtemp()
    # dir_save = r"C:\Users\lpetrucco\Desktop\stytra"
    # Here you configure the camera input
    #
    # camera_config = dict(video_file=r"J:\_Shared\stytra\fish_tail_anki.h5")
    camera_config = dict(type='ximea')

    tracking_config = dict(
        embedded=True,
        tracking_method="eyes",
        estimator="vigor",
        preprocessing_method="prefilter",
    )

    display_config = dict(full_screen=True)

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[MixedProtocol],
        camera_config=camera_config,
        tracking_config=tracking_config,
        display_config=display_config,
        # dir_save=dir_save,
        # log_format='hdf5'
    )
