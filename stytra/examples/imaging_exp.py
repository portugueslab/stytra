import numpy as np
import pandas as pd
from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import GainLagClosedLoop1D, GratingStimulus
from lightparam import Param
from pathlib import Path

# Definition of protocol class:
class ImagingCLProtocol(Protocol):
    name = "imaging_closed_loop"
    stytra_config = dict(
        tracking=dict(method="tail", estimator="vigor"),
        # To run on a setup, replace the following example file with the
        # desired camera config, such as
        # camera_config = dict(type="ximea")
        # for a ximea camera, etc.
        camera=dict(
            video_file=str(Path(__name__).parent / "assets" / "fish_compressed.h5")
        ),
        # Triggering: trigger from devices not supporting zmq messages
        # require changing this with other triggering options:
        trigger="zmq",
    )

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(20.0)
        self.grating_vel = Param(10.0)
        self.grating_duration = Param(10.0)
        self.grating_cycle = Param(10)
        self.protocol_reps = Param(2)

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
        gain_values = [0, 0, 1, 1] * self.protocol_reps

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
    Stytra(protocol=ImagingCLProtocol())
