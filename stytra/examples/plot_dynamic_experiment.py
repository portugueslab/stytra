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

        # Gratings
        v = self.grating_vel

        t_base = [0, p, p, p + d, p + d, 2 * p + d]
        vel_base = [0, 0, -v, -v, 0, 0]
        t = []
        vel = []

        t.extend(t_base)
        vel.extend(vel_base)

        df = pd.DataFrame(dict(t=t, vel_x=vel))
        stimuli.append(
            MovingGratingStimulus(
                df_param=df,
                grating_angle=0,
                grating_period=10,
                grating_col_1=(255, 0, 0),
                wave_shape=self.wave_shape,
            )
        )
        return stimuli


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(protocols=[MixedProtocol],
               stim_plot=True)
