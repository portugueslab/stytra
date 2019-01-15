from stytra import Stytra
from stytra.stimulation.stimuli import (
    MovingGratingStimulus
)

from stytra.stimulation import Protocol
from lightparam import Param
import pandas as pd


class ScreeningProtocol(Protocol):
    name = "screening"
    stytra_config = dict(
        tracking=dict(method="fish", embedded=False),
    )

    def __init__(self):
        super().__init__()
        self.grating_movement_duration = Param(20, (1, 120))
        self.grating_pause_duration = Param(10, (1, 120))
        self.n_gratings = Param(10, (0, 100))
        self.grating_velocity = Param(10, (1, 100))

    def get_stim_sequence(self):
        ts = []
        vels = []
        t = 0
        lr = -1
        for i_trial in range(self.n_gratings):
            ts.extend([t, t + self.grating_pause_duration])
            t += self.grating_pause_duration
            ts.extend([t, t+self.grating_movement_duration])
            vels.extend([0, 0, lr * self.grating_velocity, lr * self.grating_velocity])
            lr *= -1
        return [MovingGratingStimulus(df_param=pd.DataFrame(dict(t=ts, vel_x=vels)),
                                     grating_period=10)]


if __name__ == "__main__":
    s = Stytra(protocol=ScreeningProtocol())
