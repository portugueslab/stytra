from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from pathlib import Path
from stytra.stimulation import Protocol


class Nostim(Protocol):
    name = "empty_protocol"

    # In the stytra_config class attribute we specify a dictionary of
    # parameters that control camera, tracking, monitor, etc.
    # In this particular case, we add a stream of frames from one example
    # movie saved in stytra assets.
    stytra_config = dict(
        camera=dict(type="spinnaker"))

    #  For a streaming from real cameras connected to the computer, specify camera type, e.g.:
    # stytra_config = dict(camera=dict(type="ximea"))

    def get_stim_sequence(self):
        return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Nostim())
