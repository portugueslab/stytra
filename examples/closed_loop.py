import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import ClosedLoop1DGratings, SeamlessGratingStimulus


class ClosedLoop1D(Protocol):
    name = "closed_loop1D_gratings"

    def __init__(self):
        super().__init__()

        self.add_params(inter_stim_pause=20.,
                        grating_vel=10.,
                        grating_duration=10.,
                        grating_cycle=10)

    def get_stim_sequence(self):
        stimuli = []
        # # gratings
        p = 2  # self.params['inter_stim_pause']/2
        v = 10  # self.params['grating_vel']
        d = 10  # self.params['grating_duration']

        df = pd.DataFrame(dict(t=[0, p, p, p+d, p+d, 2*p + d],
                               vel=[0, 0, -v, -v, 0, 0]))

        stimuli.append(ClosedLoop1DGratings(df,
                                            grating_angle=np.pi/2,
                                            grating_period=self.params[
                                                   'grating_cycle'],
                                            color=(255, )*3))
        return stimuli


if __name__ == "__main__":

    # Reading from a file:
    # This will work only with a file!
    # TODO provide downloadable example file
    file = r"J:\_Shared\lightsheet_testing\eye_tracking\eyes_better.xiseq"
    camera_config = dict(video_file=file, rotation=1)

    # Reading from a Ximea camera:
    camera_config = dict(type="ximea")

    tracking_config = dict(embedded=True, tracking_method="angle_sweep",
                           estimator="vigor")

    display_config = dict(full_screen=True)

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[ClosedLoop1D],
        camera_config=camera_config,
        tracking_config=tracking_config,
        display_config=display_config,
        dir_save=r'D:\vilim\stytra\\',

    )
