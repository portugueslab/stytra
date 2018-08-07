from stytra import Stytra
from stytra.stimulation.stimuli import PerpendicularMotion, SeamlessImageStimulus
from stytra.stimulation import Protocol
import pandas as pd
import pkg_resources


class PerpendicularMotionProtocol(Protocol):
    name="Perpendicular motion"
    def get_stim_sequence(self):
        motion = dict(
            t=[0, 20, 20, 30],
            vel_y=[-10, -10, 10, 10]
        )
        moving_stuff = type("ClosedLoopImage",
                            (PerpendicularMotion, SeamlessImageStimulus),
                            {})
        return [moving_stuff(df_param=pd.DataFrame(motion), background="arrows.png")]


if __name__ == "__main__":
    #video_file = r"J:\Vilim Stih\fish_recordings\20180719_170349.mp4"

    #camera_config = dict(video_file=video_file, rotation=0)
    tracking_config = dict(tracking_method="fish", estimator="position")
    s = Stytra(
        camera_config=dict(type="ximea", downsampling=2),
        dir_assets=pkg_resources.resource_filename("stytra",
                                                   "tests/test_assets"),
        tracking_config=tracking_config,
        protocols=[PerpendicularMotionProtocol],
        dir_save=r"D:\stytra",
        log_format="csv",
        embedded=False,
        display_config=dict(full_screen=True)
    )
