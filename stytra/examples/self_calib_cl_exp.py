import pandas as pd
import numpy as np
from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import (
    CalibratingClosedLoop1D,
    GratingStimulus)
from lightparam import Param
from pathlib import Path


class ClosedLoop1DProt(Protocol):
    name = "self_calib_cl1D_gratings"

    stytra_config = dict(
        tracking=dict(embedded=True, method="tail", estimator="vigor"),
        camera=dict(
            video_file=str(Path(__file__).parent / "assets" / "fish_compressed.h5")
        ),
        log_format="csv",
    )

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(10)
        self.grating_vel = Param(10.)
        self.grating_duration = Param(30)
        self.grating_cycle = Param(10)
        self.target_vel = Param(-15., limits=(-50, 20))

    def get_stim_sequence(self):
        stimuli = []
        # # gratings
        p = self.inter_stim_pause / 2
        v = self.grating_vel
        d = self.grating_duration

        t_base = np.array([0, p, p, p + d, p + d, 2 * p + d])
        vel_base = np.array([0, 0, -v, -v, 0, 0])
        t = [0]
        vel = [0]

        for i in range(1):
            t.extend(t_base + t[-1])
            vel.extend(vel_base)

        df = pd.DataFrame(dict(t=t, base_vel=vel))

        ClosedLoop1DGratings = type(
            "Stim", (CalibratingClosedLoop1D, GratingStimulus), {}
        )

        stimuli.append(
            ClosedLoop1DGratings(
                df_param=df,
                grating_angle=np.pi / 2,
                grating_period=self.grating_cycle,
                target_avg_fish_vel=self.target_vel,
                calibrate_after=5
            )
        )
        return stimuli


if __name__ == "__main__":
    s = Stytra(protocol=ClosedLoop1DProt())
