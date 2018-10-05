from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from poparam import Param


class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.period_sec = Param(10., limits=(0.2, None))
        self.flash_duration = Param(1., limits=(0., None))

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=self.period_sec - self.flash_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocols=[FlashProtocol],
                dir_save='C:/Users/portugueslab/Desktop/')
    st.base.close()
