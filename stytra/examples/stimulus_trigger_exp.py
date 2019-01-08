from stytra import Stytra, Protocol
from stytra.stimulation.stimuli import Pause, FullFieldVisualStimulus, TriggerStimulus
from stytra.triggering import ZmqTrigger

# In this example, we use the TriggerStimulus to trigger the protocol at
# arbitrary points. After starting the experiment and starting the protocol,
# you will need to run the zmq_trigger script one time to start the first part
# of the protocol (a green flash),
# and another time to run the second part of the protocol (a red flash).
# Make sure that the "wait for trigger signal" box is not checked, or an additional
# triggering signal will be required at the beginning!

class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.pause_duration = 1.
        self.flash_duration = 2.

    def get_stim_sequence(self):
        stimuli = [
            TriggerStimulus(),
            Pause(duration=self.pause_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(0, 255, 0)
            ),
            Pause(duration=self.pause_duration),

            TriggerStimulus(),
            Pause(duration=self.pause_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 0, 0)
            ),
            Pause(duration=self.pause_duration),
        ]
        return stimuli


if __name__ == "__main__":
    trigger = ZmqTrigger(port="5555")
    st = Stytra(protocol=FlashProtocol(), scope_triggering=trigger)
