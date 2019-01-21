from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import StimulusCombiner, MovingGratingStimulus, \
    HighResMovingWindmillStimulus
import pandas as pd
import numpy as np
from pathlib import Path


class ConditionalCombiner(StimulusCombiner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use clip masks to respectively hide and show the two stimuli
        self.stim_list[0].clip_mask = [0, 0, 1, 1]
        self.stim_list[1].clip_mask = [0, 0, 0, 0]

    def update(self):
        fish_vel = self._experiment.estimator.get_velocity()
        # Alternate orientations depending on whether the fish is swimming
        # or not.
        if fish_vel < -5:
            self.stim_list[0].clip_mask = [0, 0, 1, 1]
            self.stim_list[1].clip_mask = [0, 0, 0, 0]
        else:
            self.stim_list[0].clip_mask = [0, 0, 0, 0]
            self.stim_list[1].clip_mask = [0, 0, 1, 1]

        super().update()


class CombinedProtocol(Protocol):
    name = "combined_custom_protocol"  # every protocol must have a name.

    stytra_config = dict(
        tracking=dict(method="tail", estimator="vigor"),
        camera=dict(
            video_file=str(
                Path(__file__).parent / "assets" / "fish_compressed.h5")
        ),
    )

    def get_stim_sequence(self):
        # This is the
        # Use six points to specify the velocity step to be interpolated:
        t = [0, 7]
        vel = np.array([10, 10])

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        s_a = MovingGratingStimulus(
                df_param=df,
                clip_mask=[0, 0, 1, 0.5])

        df = pd.DataFrame(dict(t=t, vel_x=-vel))
        s_b = MovingGratingStimulus(
            df_param=df,
            grating_angle=180,
            clip_mask=[0, 0.5, 1, 0.5])

        stimuli = [ConditionalCombiner([s_a, s_b])]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=CombinedProtocol())
