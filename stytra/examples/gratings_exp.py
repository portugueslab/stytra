import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import MovingGratingStimulus
from lightparam import Param
from pathlib import Path


class GratingsProtocol(Protocol):
    name = "gratings_protocol"

    def __init__(self):
        super().__init__()

        self.t_pre = Param(5.)  # time of still gratings before they move
        self.t_move = Param(5.)  # time of gratings movement
        self.grating_vel = Param(-10.)  # gratings velocity
        self.grating_period = Param(10)  # grating spatial period
        self.grating_angle_deg = Param(90.)  # grating orientation

    def get_stim_sequence(self):
        # Use six points to specify the velocity step to be interpolated:
        t = [
            0,
            self.t_pre,
            self.t_pre,
            self.t_pre + self.t_move,
            self.t_pre + self.t_move,
            2 * self.t_pre + self.t_move,
        ]

        vel = [0, 0, self.grating_vel, self.grating_vel, 0, 0]

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        return [
            MovingGratingStimulus(
                df_param=df,
                grating_angle=self.grating_angle_deg * np.pi / 180,
                grating_period=self.grating_period,
            )
        ]


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(protocol=GratingsProtocol())
