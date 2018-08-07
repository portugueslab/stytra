from stytra import Stytra
from stytra.stimulation.stimuli import PerpendicularMotion,\
    SeamlessImageStimulus, FishTrackingStimulus, HalfFieldStimulus, FishOverlayStimulus
from stytra.stimulation import Protocol
import pandas as pd
import pkg_resources


class PhototaxisProtocol(Protocol):
    name = "phototaxis"
    def get_stim_sequence(self):
        stim = type("phototaxis", (FishTrackingStimulus, HalfFieldStimulus), {})
        return [stim(duration=600)]


if __name__ == "__main__":
    #video_file = r"J:\Vilim Stih\fish_recordings\20180719_170349.mp4"

    #camera_config = dict(video_file=video_file, rotation=0)
    tracking_config = dict(tracking_method="fish", estimator="position")
    s = Stytra(
        camera_config=dict(type="ximea", downsampling=2),
        dir_assets=pkg_resources.resource_filename("stytra",
                                                   "tests/test_assets"),
        tracking_config=tracking_config,
        protocols=[PhototaxisProtocol],
        dir_save=r"D:\stytra",
        log_format="csv",
        embedded=False,
        display_config=dict(full_screen=True)
    )
