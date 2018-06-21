from stytra import Stytra, Protocol
from stytra.stimulation.visual import Pause, FullFieldVisualStimulus

class FlashProtocol(Protocol):
    name = 'flash protocol'

    def __init__(self):
        super().__init__()
        self.add_params(period_sec=5.,
                        flash_duration=2.)

    def get_stim_sequence(self):
        stimuli = [Pause(duration=self.params['period_sec'] -
                                  self.params['flash_duration']),
                   FullFieldVisualStimulus(duration=self.params[
                         'flash_duration'], color=(255, 255, 255))]
        return stimuli

if __name__ == "__main__":
    st = Stytra(protocols=[FlashProtocol],
                directory=r'C:\Users\lpetrucco\Desktop\metadata')
