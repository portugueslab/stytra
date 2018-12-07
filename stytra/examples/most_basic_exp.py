from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus

# 1. Define a protocol subclass
class FlashProtocol(Protocol):
    name = "flash_protocol"  # every protocol must have a name.

    def get_stim_sequence(self):
        # This is the method we need to write to create a new stimulus list.
        # In this case, the protocol is simply a 1 second flash on the entire screen
        # after a pause of 4 seconds:
        stimuli = [
            Pause(duration=4.),
            FullFieldVisualStimulus(duration=1., color=(255, 255, 255)),
        ]
        return stimuli


if __name__ == "__main__":
    # This is the line that actually opens stytra with the new protocol.
    st = Stytra(protocol=FlashProtocol())
