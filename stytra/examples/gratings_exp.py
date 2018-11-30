import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import MovingGratingStimulus
from lightparam import Param


class GratingsProtocol(Protocol):
    name = "gratings protocol"

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(5.)
        self.grating_vel = Param(10.)
        self.grating_duration = Param(5.)
        self.grating_cycle = Param(10)
        self.grating_angle_deg = Param(90.)
        self.grating_shape = Param("square", limits=["square", "sine"])

    def get_stim_sequence(self):
        stimuli = []
        # # gratings
        p = self.inter_stim_pause / 2
        v = self.grating_vel
        d = self.grating_duration

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
                grating_angle=self.grating_angle_deg * np.pi/180,
                grating_period=self.grating_cycle,
                grating_col_2=(0, 0, 0),
                wave_shape=self.grating_shape,
            )
        )
        return stimuli


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(protocol=GratingsProtocol())
