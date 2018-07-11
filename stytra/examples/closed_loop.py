import numpy as np
import pandas as pd

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import ClosedLoop1DGratings


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
        p = self.params['inter_stim_pause']/2
        v = self.params['grating_vel']
        d = self.params['grating_duration']

        t_base = [0, p, p, p + d, p + d, 2 * p + d]
        vel_base = [0, 0, -v, -v, 0, 0]
        t = []
        vel = []
        gain = []
        gain_values = [0, 0.5, 1, 1.5]
        np.random.shuffle(gain_values)

        t.extend(t_base)
        vel.extend(vel_base)
        gain.extend([0, 0, gain_values[0], gain_values[0], 0, 0])

        # Low, medium, high gain:
        for g in [0.5, 1, 1.5]:
            t.extend(t[-1] + np.array(t_base))
            vel.extend(vel_base)
            gain.extend([0, 0, g, g, 0, 0])

        df = pd.DataFrame(dict(t=t, vel=vel, gain=gain))

        stimuli.append(ClosedLoop1DGratings(df_param=df,
                                            grating_angle=np.pi/2,
                                            grating_period=self.params[
                                                   'grating_cycle'],
                                            grating_col_1=(255, )*3))
        return stimuli


if __name__ == "__main__":
    save_dir = r'/Users/vilimstich/PhD/Experimental/'
    camera_config = dict(video_file="/Users/vilimstich/PhD/Experimental/fish_tail.h5")

    tracking_config = dict(
        embedded=True, tracking_method="angle_sweep", estimator="vigor"
    )

    display_config = dict(full_screen=True)

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[ClosedLoop1D],
        camera_config=camera_config,
        tracking_config=tracking_config,
        display_config=display_config,
        dir_save=save_dir,
    )
