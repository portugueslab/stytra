from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from lightparam import Param


class FlashProtocol(Protocol):
    name = "flash_protocol"  # every protocol must have a name.

    def __init__(self):
        super().__init__()
        # Here we define these attributes as Param s. This will automatically
        #  build a control for them and make them modifiable live from the
        # interface.
        self.period_sec = Param(10., limits=(0.2, None))
        self.flash_duration = Param(1., limits=(0., None))

    def get_stim_sequence(self):
        # This is the
        stimuli = [
            Pause(duration=self.period_sec - self.flash_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=FlashProtocol())
