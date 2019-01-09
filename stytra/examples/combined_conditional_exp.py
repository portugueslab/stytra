from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import StimulusCombiner, MovingGratingStimulus, \
    HighResMovingWindmillStimulus, FullFieldVisualStimulus
import pandas as pd
import numpy as np
from pathlib import Path

# This stimulus combiner alternatively display one of the first two stimuli of
# the list when the fish is swimming.
class ConditionalCombiner(StimulusCombiner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use clip masks to respectively hide and show the two stimuli
        self.stim_list[0].clip_mask = [0, 0, 1, 1]
        self.stim_list[1].clip_mask = [0, 0, 0, 0]

        self.toggle = False

    def update(self):
        super().update()
        fish_vel = self._experiment.estimator.get_velocity()
        # change color if speed of the fish is higher than threshold:
        # print(self.stim_list[0].clip_mask)

        if fish_vel < -5:
            # Show alternated gratings to the left and to the right
            # when the fish is moving:
            self.stim_list[2].clip_mask = [0, 0, 0, 0]
            self.toggle = not self.toggle
            if self.toggle:
                self.stim_list[0].clip_mask = [0, 0, 1, 1]
                self.stim_list[1].clip_mask = [0, 0, 0, 0]
            else:
                self.stim_list[0].clip_mask = [0, 0, 0, 0]
                self.stim_list[1].clip_mask = [0, 0, 1, 1]

        else:
            # Hide stimuli:
            self.stim_list[0].clip_mask = [0, 0, 0, 0]
            self.stim_list[1].clip_mask = [0, 0, 0, 0]
            self.stim_list[2].clip_mask = [0, 0, 1, 1]


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
        t = [0, 15]
        vel = np.array([10, 10])

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        s_a = MovingGratingStimulus(
                df_param=df)

        df = pd.DataFrame(dict(t=t, vel_x=vel))
        s_b = MovingGratingStimulus(
            grating_angle=np.pi/2,
            df_param=df)

        s_mask = FullFieldVisualStimulus(duration=t[-1], color=(0, 0, 0))

        stimuli = [ConditionalCombiner([s_a, s_b, s_mask])]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=CombinedProtocol())
