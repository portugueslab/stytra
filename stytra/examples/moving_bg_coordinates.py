from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import (
    SeamlessImageStimulus,
    InterpolatedStimulus,
)
from stytra.stimulation.stimuli import FishRelativeStimulus
from stytra.stimulation.estimators import SimulatedPositionEstimator
import pandas as pd
from pathlib import Path
from lightparam import Param
import numpy as np


class BackgroundProtocol(Protocol):
    name = "background_protocol"  # every protocol must have a name.
    stytra_config = dict(
        tracking=dict(
            method="fish",
            embedded=False,
            estimator=SimulatedPositionEstimator,
            estimator_params=dict(
                motion=pd.DataFrame(
                    dict(
                        t=[0, 5, 120],
                        x=[100, 100, 100],
                        y=[10, 10, 10],
                        theta=[0, 0, np.pi / 2],
                    )
                )
            ),
        ),
        camera=dict(
            video_file=str(
                Path(__file__).parent / "assets" / "fish_free_compressed.h5"
            ),
            min_framerate=100,
        ),
    )

    def __init__(self):
        super().__init__()
        self.theta = Param(0, (-360, 360))
        self.delta = Param(0, (-360, 360))

    def get_stim_sequence(self):
        # This is the
        MovingStim = type(
            "MovingStim",
            (FishRelativeStimulus, InterpolatedStimulus, SeamlessImageStimulus),
            dict(),
        )
        motion_df = pd.DataFrame(
            dict(
                t=[0, 10, 20],  #  4,  4,   8,  8,  12,  12],
                x=[50, 50, 500],  # ,100,100, 100, 100, 0, 0],
                y=[50, 50, 50],
            )
        )  # , 0,  0,  100, 100, 100, 100]))

        stimuli = [
            MovingStim(
                background=Path(__file__).parent / "assets" / "coordinate_system.png",
                df_param=motion_df,
                duration=300,
                x=self.delta,
                y=self.delta,
                theta=self.theta * np.pi / 180,
            )
        ]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=BackgroundProtocol())
