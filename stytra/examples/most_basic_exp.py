from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus


class FlashProtocol(Protocol):
    name = "flash_protocol"  # every protocol must have a name.

    def __init__(self):
        super().__init__()

    def get_stim_sequence(self):
        # This is the
        stimuli = [
            Pause(duration=4.
                duration=1, color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=FlashProtocol())
