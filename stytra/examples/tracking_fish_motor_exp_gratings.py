from stytra import Stytra
from stytra.stimulation.stimuli import Pause
from stytra.stimulation import Protocol
from lightparam import Param
import datetime
from collections import namedtuple
from pathlib import Path
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli.conditional import adaptiveRadialSineStimulus, RadialSineStimulus
from stytra.stimulation.stimuli.conditional import CenteringWrapper,\
    TwoRadiusCenteringWrapper, MottiCenteringWrapper
from stytra.stimulation.stimuli.visual import FullFieldVisualStimulus
from stytra import Stytra
from stytra.stimulation.stimuli.conditional import adaptiveRadialSineStimulus, RadialSineStimulus
from stytra.stimulation.stimuli.conditional import CenteringWrapper,\
    TwoRadiusCenteringWrapper, MottiCenteringWrapper

from stytra.stimulation.stimuli import (
    MovingGratingStimulus,
    GratingStimulus,
    PositionStimulus,
    BackgroundStimulus,
)

from PyQt5.QtGui import QTransform

from stytra.stimulation.stimuli.conditional import TwoRadiusCenteringWrapper, MottiCenteringWrapper
from stytra.stimulation import Protocol
from lightparam import Param
import pandas as pd
import numpy as np

class FishRelativeRotationOnlyStimulus(BackgroundStimulus):
    def __init__(self, *args, theta_change_threshold=12 * np.pi / 180, **kwargs):
        super().__init__(*args, **kwargs)
        self.stored_fish_theta = None
        self.fish_theta_change_threshold = theta_change_threshold

    @property
    def theta_total(self):
        if self.stored_fish_theta is not None:
            return self.theta + self.stored_fish_theta - np.pi / 2
        return self.theta

    def get_transform(self, w, h, x, y):
        _, _, theta_fish = self._experiment.estimator.get_position() # underscore means that this will be discarded
        if self.stored_fish_theta is None or \
                np.abs(np.mod(theta_fish-self.stored_fish_theta, 2*np.pi)) > self.fish_theta_change_threshold:
            self.stored_fish_theta = theta_fish

        rot_fish = (self.stored_fish_theta - np.pi / 2) * 180 / np.pi
        xc = w/2
        yc = h/2
        return super().get_transform(w, h, x, y) * (QTransform().translate(xc, yc).rotate(rot_fish).translate(-xc, -yc))


class GratingsTrackingStimulus(FishRelativeRotationOnlyStimulus, MovingGratingStimulus):
    pass


class FullFieldVisualStimulus2(FullFieldVisualStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self):
        t = datetime.datetime.now()
        # tracking, waiting
        sec_output = (True, False)
        self._experiment.send_motor_status(t, sec_output)
        super().update()



class Motti(Protocol):
    name = "motti_protocol"
    stytra_config = dict(
        camera=dict(type="spinnaker"), tracking=dict(method="fish_motor_bg",estimator="position"),
        recording=dict(extension="mp4", kbit_rate=3000),
        motor=dict())

    def __init__(self):
        super().__init__()

        self.period_sec = Param(10., limits=(0.2, None))
        self.flash_duration = Param(1., limits=(0., None))

        self.inter_stim_pause = Param(10., limits=(0, 300))
        self.grating_vel = Param(10., limits=(-50, 50))
        self.grating_duration = Param(15., limits=(0, 300))
        self.grating_cycle = Param(5, limits=(0, 300))  # spatial period of the grating
        self.n_rep_internal = Param(10, limits=(0, 300))  # nr of total red and green alternations (10 each; 20 total)
        self.green = Param(90, limits=(0, 255))
        self.red = Param(255, limits=(0, 255))
        self.r_out = Param(45, limits=(10, 50))
        self.r_in = Param(35, limits=(10, 50))



    def get_stim_sequence(self):
        p = self.inter_stim_pause / 2
        v = self.grating_vel
        d = self.grating_duration

        t = [0, p, p, p + d, p + d, 2 * p + d, 2 * p + d, 2 * (p + d), 2 * (p + d), 2 * (p + d) + p]
        vel = [0, 0, v, v, 0, 0, -v, -v, 0, 0]

        df = pd.DataFrame(dict(t=t, vel_x=vel))

        # This is the
        # stimuli = [
        #     MottiCenteringWrapper(stimulus=
        #     FullFieldVisualStimulus2(
        #         duration=self.flash_duration, color=(255, 255, 255)
        #     ),centering_stimulus =RadialSineStimulus(period=1, velocity=5, duration=1)),
        # ]

        stimuli =[(MottiCenteringWrapper(stimulus=GratingsTrackingStimulus(
                            df_param=df,
                            grating_period=self.grating_cycle,
                            grating_col_1=(0, self.green, 0),
                            grating_angle=0,
                        ),  r_out=45, r_in=40,centering_stimulus=RadialSineStimulus(period=2, velocity=5, duration=1))
                    )]


        return stimuli

        # return [Pause(duration=10)]  # protocol does not do anything


if __name__ == "__main__":
    s = Stytra(protocol=Motti())

