import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol

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
    tracking_config = dict(camera='ximea',
                           video_file=None,
                           camera_rotation=1,
                           tracking_method_name='centroid')

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(protocols=[LoomingProtocol], tracking_config=tracking_config,
               directory=r'C:\Users\portugueslab\data\stytra')