from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus


class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.add_params(period_sec=5., flash_duration=2.)

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=self.params["period_sec"] - self.params["flash_duration"]),
            FullFieldVisualStimulus(
                duration=self.params["flash_duration"], color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":

    # Reading from a file:
    # This will work only with a file!
    # TODO provide downloadable example file
    file = r"J:\_Shared\stytra\fish_tail.h5"
    camera_config = dict(video_file=file, rotation=1)

    # Reading from a Ximea camera:
    # camera_config = dict(type="ximea")

    tracking_config = dict(
        embedded=True, tracking_method="angle_sweep",
        preprocessing_method="prefilter"
    )

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[FlashProtocol],
        camera_config=camera_config,
        tracking_config=tracking_config,
        dir_save=r"D:\vilim\stytra\\",
    )
