from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from stytra.stimulation import Protocol

REQUIRES_EXTERNAL_HARDWARE = False


class Nostim(Protocol):
    name = "empty_protocol"

    stytra_config = dict(camera=dict(type="opencv"))

    def get_stim_sequence(self):
        return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Nostim())
