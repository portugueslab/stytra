from stytra import Stytra
from stytra.stimulation.stimuli import (
    FishTrackingStimulus,
    HalfFieldStimulus,
    RadialSineStimulus,
    FullFieldVisualStimulus,
)
from stytra.stimulation.stimuli.conditional import CenteringWrapper

from stytra.stimulation import Protocol
from lightparam import Param
from pathlib import Path


class PhototaxisProtocol(Protocol):
    name = "phototaxis"
    stytra_config = dict(
        display=dict(min_framerate=50),
        tracking=dict(method="fish", embedded=False, estimator="position"),
        camera=dict(
            video_file=str(Path(__file__).parent / "assets" / "fish_free_compressed.h5"),
            min_framerate=100,
        ),
    )

    def __init__(self):
        super().__init__()
        self.n_trials = Param(120, (0, 2400))
        self.stim_on_duration = Param(10, (0, 30))
        self.stim_off_duration = Param(10, (0, 30))
        self.center_offset = Param(0, (-100, 100))
        self.brightness = Param(255, (0, 255))

    def get_stim_sequence(self):
        centering = RadialSineStimulus(duration=self.stim_on_duration)
        stimuli = []
        stim = type("phototaxis", (FishTrackingStimulus, HalfFieldStimulus), {})
        for i in range(self.n_trials):
            stimuli.append(
                CenteringWrapper(
                    stimulus=stim(
                        duration=self.stim_on_duration,
                        color=(self.brightness,) * 3,
                        center_dist=self.center_offset,
                    ),
                )
            )
            stimuli.append(
                FullFieldVisualStimulus(
                    color=(self.brightness,) * 3, duration=self.stim_off_duration
                )
            )

        return stimuli


if __name__ == "__main__":
    s = Stytra(protocol=PhototaxisProtocol())
