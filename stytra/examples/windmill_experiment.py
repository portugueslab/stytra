import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import MovingWindmillStimulus, \
    MovingGratingStimulus


class MixedProtocol(Protocol):
    name = "closed_loop1D_gratings"

    def __init__(self):
        super().__init__()

        self.add_params(inter_stim_pause=2.,
                        theta_amp=np.pi/2,
                        windmill_freq=0.2,
                        grating_vel=10,
                        stim_duration=5.,
                        wave_shape=dict(values=['square', 'sinusoidal']),
                        n_arms=10
                        )

    def get_stim_sequence(self):
        stimuli = []
        p = self.params['inter_stim_pause'] / 2
        d = self.params['stim_duration']

        # Windmill
        STEPS = 0.005
        t = np.arange(0, d, STEPS)
        theta = np.sin(2*np.pi*t*self.params['windmill_freq']) * \
                self.params['theta_amp']

        t = [t[0], ] + list(t+p) + [(t+2*p)[-1], ]
        theta = [theta[0], ] + list(theta) + [theta[-1], ]
        df = pd.DataFrame(dict(t=t, theta=theta))
        stimuli.append(
            MovingWindmillStimulus(df_param=df))

        # Gratings
        v = self.params['grating_vel']

        t_base = [0, p, p, p + d, p + d, 2 * p + d]
        vel_base = [0, 0, -v, -v, 0, 0]
        t = []
        vel = []

        t.extend(t_base)
        vel.extend(vel_base)

        df = pd.DataFrame(dict(t=t, vel_x=vel))
        stimuli.append(
            MovingGratingStimulus(df_param=df,
                                  grating_angle=0,
                                  grating_period=10,
                                  grating_col_1=(255, 0, 0),
                                  wave_shape='sinusoidal'))
        return stimuli


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[MixedProtocol],
        dir_assets=r'J:\_Shared\myelination\OKR\round7',
        stim_plot=True
    )
