import numpy as np
import pandas as pd
from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import ClosedLoop1D, GratingStimulus
from lightparam import Param

# Here we present the code used for the replication of the Portugues et al
# 2011 paper, as presented in [cit. stytra].
# Running this script on a setup configured according to the stytra
# configuration should allow for the replication of the same experimental
# conditions.

# Definition of protocol class:
class Portugues2011Protocol(Protocol):
    name = "portugues_2011"
    stytra_config = dict(
        tracking_config=dict(
            tracking_method="tail",
            estimator="vigor"
        ),
        # Replace this example file with the desired camera config, such as
        # camera_config = dict(type="ximea")
        # for a ximea camera, etc. Not needed if the setup already has the
        # stytra_setup_config.json file
        camera_config=dict(
            video_file=r"J:\_Shared\stytra\fish_tail_anki.h5"
        ),
    )

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(20.)
        self.grating_vel = Param(10.)
        self.grating_duration = Param(10.)
        self.grating_cycle = Param(10)
        self.low_gain = Param(0.5)
        self.high_gain = Param(1.5)
        self.protocol_reps = Param(6)

    def get_stim_sequence(self):
        stimuli = []

        # In the following part we create a dataframe with the velocity and the
        # gain steps that will be interpolated by the stimulus class.
        # The approach is to define many segments, where every segment
        # correspond to a moving grating lead and followed
        p = self.inter_stim_pause / 2  #
        v = self.grating_vel
        d = self.grating_duration

        gain_values = ([1] * 3 +
                       [self.high_gain] * 3 +
                       [self.low_gain] * 3 +
                       [1] * 3 +
                       [self.low_gain] * 3 +
                       [self.high_gain] * 3) * n_reps

        t_base = [0, p, p, p + d, p + d, 2 * p + d]
        vel_base = [0, 0, -v, -v, 0, 0]
        t = [0]
        vel = [0]
        gain = [0]
        n_reps = self.protocol_reps

        # t.extend(t_base)
        # vel.extend(vel_base)
        # gain.extend([0] * 2 + [gain_values[0]] * 2 + [0] * 2)

        # Low, medium, high gain:
        for g in gain_values:
            t.extend(t[-1] + np.array(t_base))
            vel.extend(vel_base)
            gain.extend([0] * 2 + [g] * 2 + [0] * 2)

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
    Stytra(Portugues2011Protocol())

