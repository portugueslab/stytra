from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from pathlib import Path
from stytra.stimulation import Protocol


class Nostim(Protocol):
    name = "empty protocol"
    stytra_config = dict(camera=dict(
        video_file=str(Path(__name__).parent / "assets" / "fish_compressed.h5")))

    def get_stim_sequence(self):
        return [Pause(duration=10)]


if __name__ == "__main__":
    pass
    s = Stytra(protocol=Nostim())
#