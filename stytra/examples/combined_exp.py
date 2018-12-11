from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import StimulusCombiner, MovingGratingStimulus, \
    HighResMovingWindmillStimulus
import pandas as pd
import numpy as np


class CombinedProtocol(Protocol):
    name = "combined_protocol"  # every protocol must have a name.

    def get_stim_sequence(self):
        # This is the
        # Use six points to specify the velocity step to be interpolated:
        t = [0, 1, 1, 6, 6, 7]
        vel = np.array([0, 0, 10, 10, 0, 0])

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        s_a = MovingGratingStimulus(
                df_param=df,
                clip_mask=[0, 0, 1, 0.5])

        df = pd.DataFrame(dict(t=t, vel_x=-vel))
        s_b = MovingGratingStimulus(
            df_param=df,
            grating_angle=45,
            clip_mask=[0, 0.5, 1, 0.5])

        p = 1
        d = 5

        # Windmill
        STEPS = 0.005
        t = np.arange(0, d, STEPS)
        theta = np.sin(2 * np.pi * t * 0.2) * np.pi / 2

        t = [t[0]] + list(t + p) + [(t + 2 * p)[-1]]
        theta = [theta[0]] + list(theta) + [theta[-1]]
        df = pd.DataFrame(dict(t=t, theta=theta))

        s_c = HighResMovingWindmillStimulus(df_param=df, clip_mask=0.3)

        stimuli = [StimulusCombiner([s_a, s_b, s_c])]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=CombinedProtocol())
