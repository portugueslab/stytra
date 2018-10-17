from stytra import Stytra
from stytra.stimulation.stimuli import (
    Pause
)

from stytra.stimulation import Protocol
import pkg_resources
import tempfile


class Nostim(Protocol):
    def get_stim_sequence(self):
        return [Pause(duration=10)]


if __name__ == "__main__":
    video_file = r"J:\Vilim Stih\fish_recordings\old\20180719_170349.mp4"
    tempdir = tempfile.gettempdir()

    camera_config = dict(video_file=video_file, rotation=0)
    #camera_config = dict(type="imaq")
    s = Stytra(
        camera_config=camera_config,
        dir_assets=pkg_resources.resource_filename("stytra", "tests/test_assets"),
        protocols=[Nostim],
        dir_save=tempdir,
        log_format="csv",
        embedded=False,
        display_config=dict(full_screen=False),
    )
