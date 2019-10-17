
from stytra.stimulation import Protocol, Pause

from lightparam import Param


from stytra import Stytra

# Here ve define an empty protocol:
class PauseProtocol(Protocol):
    name = "camera_recording_protocol"  # every protocol must have a name.

    def __init__(self):
        super().__init__()
        self.period_sec = Param(10.0, limits=(0.2, None))

    def get_stim_sequence(self):
        return [Pause(duration=self.period_sec)]


if __name__ == "__main__":
    st = Stytra(protocol=PauseProtocol(), recording=True)
