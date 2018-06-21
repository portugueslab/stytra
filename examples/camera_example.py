from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.visual import Pause, FullFieldVisualStimulus

import pandas as pd
import numpy as np


class FlashProtocol(Protocol):
    name = 'flash protocol'

    def __init__(self):
        super().__init__()
        self.add_params(period_sec=5.,
                        flash_duration=2.)

    def get_stim_sequence(self):
        stimuli = [Pause(duration=self.params['period_sec'] -
                                  self.params['flash_duration']),
                   FullFieldVisualStimulus(duration=self.params[
                         'flash_duration'], color=(255, 255, 255))]
        return stimuli

if __name__ == "__main__":
    file = r'J:\_Shared\lightsheet_testing\eye_tracking\eyes_better.xiseq'
    camera_config = dict(video_file=file,
                         rotation=1)

    tracking_config = dict(embedded=True,
                           tracking_method="angle_sweep")

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(protocols=[FlashProtocol], camera_config=camera_config,
               tracking_config=tracking_config,
               data_dir=r'C:\Users\lpetrucco\data\stytra')
