from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.triggering import ZmqTrigger


class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.period_sec = 3.
        self.flash_duration = 2.

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=self.period_sec - self.flash_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    trigger = ZmqTrigger(port="5555")
    st = Stytra(protocol=FlashProtocol(), scope_triggering=trigger)
