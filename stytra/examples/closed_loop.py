import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import ClosedLoop1D, GratingStimulus
from lightparam import Param


class ClosedLoop1DProt(Protocol):
    name = "closed_loop1D_gratings"

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
        gain = []
        gain_values = [0, 0.5, 1, 1.5]
        np.random.shuffle(gain_values)

        t.extend(t_base)
        vel.extend(vel_base)
        gain.extend([0, 0, gain_values[0], gain_values[0], 0, 0])

        # Low, medium, high gain:
        # for g in gain_values:
        #     t.extend(t[-1] + np.array(t_base))
        #     vel.extend(vel_base)
        #     gain.extend([0, 0, g, g, 0, 0])

        df = pd.DataFrame(dict(t=t, base_vel=vel, gain=gain))

        ClosedLoop1DGratings = type("Stim", (ClosedLoop1D, GratingStimulus), {})

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
    # save_dir = tempfile.mkdtemp()
    dir_save = r"C:\Users\lpetrucco\Desktop\stytra"
    # Here you configure the camera input
    #
    camera_config = dict(video_file=r"C:\Users\lpetrucco\Desktop\fish_tail_anki.h5")
    # camera_config = dict(type='ximea')

    tracking_config = dict(
        embedded=True,
        tracking_method="centroid",
        estimator="vigor",
        preprocessing_method="prefilter",
    )

    display_config = dict(full_screen=True)

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[ClosedLoop1DProt],
        camera_config=camera_config,
        tracking_config=tracking_config,
        display_config=display_config,
        dir_save=dir_save,
        # log_format='hdf5'
    )
