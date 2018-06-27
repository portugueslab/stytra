from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.triggering import ZmqTrigger


class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.add_params(period_sec=5., flash_duration=2.)

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=self.params["period_sec"] - self.params["flash_duration"]),
            FullFieldVisualStimulus(
                duration=self.params["flash_duration"], color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    # trigger = Crappy2PTrigger(r'C:\Users\lpetrucco\Desktop\dummydir')
    # trigger.start()
    trigger = ZmqTrigger(port="5555")
    st = Stytra(
        protocols=[FlashProtocol],
        trigger=trigger,
        directory=r"C:\Users\portugueslab\Desktop\metadata",
    )
    # trigger.terminate_event.set()
    # print('terminating')
    # trigger.join()
