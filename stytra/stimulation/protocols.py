from stytra.stimulation import Protocol
from stytra.stimulation.visual import Pause


class NoStimulation(Protocol):
    """ A protocol without stimulation
    """
    name = 'no stimulation'

    def __init__(self):
        super().__init__()
        self.add_params(duration=5)

    def get_stim_sequence(self):
        return [Pause(duration=self.params['duration'])]

