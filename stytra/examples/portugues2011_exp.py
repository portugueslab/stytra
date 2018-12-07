import numpy as np
import pandas as pd
from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import GainLagClosedLoop1D, GratingStimulus
from lightparam import Param
from pathlib import Path

# Here we present the code used for the replication of the Portugues et al
# 2011 paper, as presented in [cit. stytra].
# The protocol defined presents the fish with white and black gratings
#  moving backward with repect to the fish. When the fish swims they are
# dragged forward according to the estimated fish velocity, in a closed loop
# configuration. This is implemented in the ClosedLoop1DGratings class. The
# gain that converts the tail sdisplacement to grating movements is modified
# every three grating movements. Gain 1 means normal velocity (around 20 mm/s
#  maximum in a bout). Gains 0.5 and 1.5 are defined accordingly.

# Running this script on a setup configured according to the stytra
# configuration should allow for the replication of the same experimental
# conditions.

# Definition of protocol class:
class Portugues2011Protocol(Protocol):
    name = "portugues_2011"
    stytra_config = dict(
        tracking=dict(method="tail", estimator="vigor"),
        camera=dict(
            video_file=str(Path(__name__).parent / "assets" / "fish_compressed.h5")
        ),
        # Replace this example file with the desired camera config, such as
        # camera_config = dict(type="ximea")
        # for a ximea camera, etc. Not needed if the setup already has the
        # # stytra_setup_config.json file
        # camera_config=dict(
        #     video_file=r"J:\_Shared\stytra\fish_tail_anki.h5"
        # ),
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
        n_reps = self.protocol_reps

        # Define the sequence of the gain values we will use, and then repeat
        #  it n_reps times
        gain_values = (
            [1] * 3
            + [self.high_gain] * 3
            + [self.low_gain] * 3
            + [1] * 3
            + [self.low_gain] * 3
            + [self.high_gain] * 3
        ) * n_reps

        t_base = [0, p, p, p + d, p + d, 2 * p + d]
        vel_base = [0, 0, -v, -v, 0, 0]
        t = [0]
        vel = [0]
        gain = [0]

        # Low, medium, high gain:
        for g in gain_values:
            t.extend(t[-1] + np.array(t_base))
            vel.extend(vel_base)
            gain.extend([0] * 2 + [g] * 2 + [0] * 2)

        df = pd.DataFrame(dict(t=t, base_vel=vel, gain=gain))

        ClosedLoop1DGratings = type("Stim", (GainLagClosedLoop1D, GratingStimulus), {})

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
    Stytra(protocol=Portugues2011Protocol())
