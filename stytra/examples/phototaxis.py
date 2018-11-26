from stytra import Stytra
from stytra.stimulation.stimuli import (
    FishTrackingStimulus,
    HalfFieldStimulus,
    RadialSineStimulus,
    CenteringWrapper,
)

from stytra.stimulation import Protocol
import pkg_resources
import tempfile
from lightparam import Param


class PhototaxisProtocol(Protocol):
    name = "phototaxis"
    stytra_config = dict(tracking=dict(method="fish", embedded=False, estimator="position"))

    def __init__(self):
        super().__init__()
        self.duration = Param(600, (0, 2400))
        self.center_offset = Param(0, (-100, 100))
        self.brightness = Param(255, (0, 255))

    def get_stim_sequence(self):
        centering = RadialSineStimulus(duration=self.duration)
        stim = type("phototaxis", (FishTrackingStimulus, HalfFieldStimulus), {})
        return [
            CenteringWrapper(
                stim(
                    duration=self.duration,
                    color=(self.brightness,) * 3,
                    center_dist=self.center_offset,
                ),
                centering,
            )
        ]


if __name__ == "__main__":
    s = Stytra(protocol=PhototaxisProtocol())
