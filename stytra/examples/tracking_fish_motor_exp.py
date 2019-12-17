from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from stytra.stimulation import Protocol
from lightparam import Param
from pathlib import Path
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli.conditional import CenteringWrapper
from stytra.stimulation.stimuli.visual import FullFieldVisualStimulus

class Motti(Protocol):
    name = "motti_protocol"
    stytra_config = dict(
        camera=dict(type="spinnaker"), tracking=dict(method="fish"),
        recording=dict(extension="mp4", kbit_rate=3000),
        motor=dict(),
        estimator="position")

    def __init__(self):
        super().__init__()

        self.period_sec = Param(10., limits=(0.2, None))
        self.flash_duration = Param(1., limits=(0., None))


    def get_stim_sequence(self):
        # This is the
        # stimuli = [
        #     CenteringWrapper(stimulus=
        #     FullFieldVisualStimulus(
        #         duration=self.flash_duration, color=(255, 255, 255)
        #     )),
        # ]

        stimuli = [
            Pause(duration=self.period_sec - self.flash_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 255, 255)
            ),
        ]
        return stimuli

        # return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Motti())
