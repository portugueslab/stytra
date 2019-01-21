import numpy as np
import pandas as pd
from pathlib import Path

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import Basic_CL_1D, GratingStimulus
from lightparam import Param


class ClosedLoop1DProt(Protocol):
    name = "closed_loop1D_gratings"

    stytra_config = dict(
        display=dict(min_framerate=50),
        tracking=dict(embedded=True, method="tail", estimator="vigor"),
        camera=dict(
            min_framerate=60,
            video_file=str(Path(__file__).parent / "assets" / "fish_compressed.h5")
        ),
    )

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(20.)
        self.grating_vel = Param(10.)
        self.grating_duration = Param(10.)
        self.grating_cycle = Param(10.)

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

        df = pd.DataFrame(dict(t=t, base_vel=vel))

        ClosedLoop1DGratings = type("Stim", (Basic_CL_1D, GratingStimulus), {})

        stimuli.append(
            ClosedLoop1DGratings(
                df_param=df,
                grating_angle=np.pi / 2,
                grating_period=self.grating_cycle,
                grating_col_1=(255,) * 3,
            )
        )
        return stimuli


if __name__ == "__main__":
    s = Stytra(protocol=ClosedLoop1DProt())
