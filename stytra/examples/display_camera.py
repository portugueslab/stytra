from stytra import Stytra
from stytra.stimulation.stimuli import Pause

from stytra.stimulation import Protocol
import pkg_resources
import tempfile


class Nostim(Protocol):
    name = "empty protocol"

    def get_stim_sequence(self):
        return [Pause(duration=10)]


if __name__ == "__main__":
    video_file = r"J:\Vilim Stih\fish_recordings\old\20180719_170349.mp4"
    tempdir = tempfile.gettempdir()

    s = Stytra(
        protocol=Nostim(),
    )
