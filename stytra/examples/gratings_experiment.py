import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import MovingGratingStimulus


class GratingsProtocol(Protocol):
    name = "closed_loop1D_gratings"

    def __init__(self):
        super().__init__()

        self.add_params(
            inter_stim_pause=100., grating_vel=1., grating_duration=5., grating_cycle=10
        )

    def get_stim_sequence(self):
        stimuli = []
        # # gratings
        p = self.params["inter_stim_pause"] / 2
        v = self.params["grating_vel"]
        d = self.params["grating_duration"]

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
                grating_period=self.params["grating_cycle"],
                grating_col_2=(0, 0, 255),
                grating_type="sine",
            )
        )
        return stimuli


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[GratingsProtocol], dir_assets=r"J:\_Shared\myelination\OKR\round7"
    )
