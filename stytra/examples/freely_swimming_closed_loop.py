from stytra import Stytra
from stytra.stimulation.stimuli import (
    FishTrackingStimulus,
    HalfFieldStimulus,
    RadialSineStimulus,
    CenteringWrapper,
)

from stytra.stimulation import Protocol
import pkg_resources
import tempfile
from lightparam import Param


class PhototaxisProtocol(Protocol):
    name = "phototaxis"

    def __init__(self):
        super().__init__()
        self.duration = Param(600)
        self.center_offset = Param(0, (-100, 100))
        self.brightness = Param(255, (0, 255))

    def get_stim_sequence(self):
        centering = RadialSineStimulus(duration=self.duration)
        stim = type("phototaxis", (FishTrackingStimulus, HalfFieldStimulus), {})
        return [CenteringWrapper(stim(duration=self.duration,
                                      color=(self.brightness,)*3,
                                      center_dist=self.center_offset,), centering)]


if __name__ == "__main__":
    video_file = r"J:\Vilim Stih\fish_recordings\old\20180719_170349.mp4"
    tempdir = tempfile.gettempdir()

    camera_config = dict(video_file=video_file, rotation=0)
    #camera_config = dict(type="imaq")
    tracking_config = dict(tracking_method="fish", estimator="position")
    s = Stytra(
        camera_config=camera_config,
        dir_assets=pkg_resources.resource_filename("stytra", "tests/test_assets"),
        tracking_config=tracking_config,
        protocols=[PhototaxisProtocol],
        dir_save=tempdir,
        log_format="csv",
        embedded=False,
        display_config=dict(full_screen=False),
    )
