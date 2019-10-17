from pathlib import Path
import numpy as np
import pandas as pd
from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import (
    MovingWindmillStimulus,
    FullFieldVisualStimulus,
    StimulusCombiner,
)
from lightparam import Param


class WindmillProtocol(Protocol):
    name = "visual_acuity_protocol"

    # To add tracking to a protocol, we simply need to add a tracking
    # argument to the stytra_config:
    stytra_config = dict(
        tracking=dict(embedded=True, method="eyes"),
        camera=dict(
            video_file=str(Path(__file__).parent / "assets" / "fish_compressed.h5")
        ),
    )

    def __init__(self):
        super().__init__()

        self.inter_stim_pause = Param(10.0)
        self.theta_amp = Param(np.pi / 2)
        self.windmill_freq = Param(0.2)
        self.stim_duration = Param(20.0)
        self.wave_shape = Param(value="sinusoidal", limits=["square", "sinusoidal"])
        self.n_arms_min = Param(10)
        self.n_arms_max = Param(60)
        self.n_arms_steps = Param(5)

    def get_stim_sequence(self):
        stimuli = []
        p = self.inter_stim_pause / 2
        d = self.stim_duration

        # Windmill
        STEPS = 0.005
        t = np.arange(0, d, STEPS)
        theta = np.sin(2 * np.pi * t * self.windmill_freq) * self.theta_amp

        t = [t[0]] + list(t + p) + [(t + 2 * p)[-1]]
        theta = [theta[0]] + list(theta) + [theta[-1]]
        df = pd.DataFrame(dict(t=t, theta=theta))

        for n_arms in range(self.n_arms_min, self.n_arms_max, self.n_arms_steps):
            windmill = MovingWindmillStimulus(
                df_param=df, n_arms=n_arms, wave_shape=self.wave_shape
            )
            pause = FullFieldVisualStimulus(duration=d, clip_mask=0.1, color=(0, 0, 0))
            stimuli.append(StimulusCombiner(stim_list=[windmill, pause]))

        return stimuli


if __name__ == "__main__":
    # We make a new instance of Stytra with this protocol as the only option:
    s = Stytra(protocol=WindmillProtocol())
