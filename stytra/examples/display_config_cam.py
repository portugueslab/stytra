from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from pathlib import Path
from stytra.stimulation import Protocol


class Nostim(Protocol):
    name = "empty_protocol"
    def get_stim_sequence(self):
        return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Nostim())
