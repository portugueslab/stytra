
import numpy as np
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor
from stytra.stimulation.stimuli.generic_stimuli import DynamicStimulus
from stytra.stimulation.stimuli.visual import (
    RadialSineStimulus,
    adaptiveRadialSineStimulus,
)
import datetime
from collections import namedtuple
from stytra.stimulation.stimuli.conditional import TwoRadiusCenteringWrapper

class MottiCenteringWrapper(TwoRadiusCenteringWrapper):
    """Extension of Two Radius centering Wrapper with adaptive location of
    Wrapper center for Motti"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.home = 2200000

    def update(self):
        t = datetime.datetime.now()
        # tracking, waiting
        waiting_status = (False, True)
        self._experiment.send_motor_status(t, waiting_status)
        super().update()

    # todo get motor pos in- if motor pos not home dont display

    def check_condition_on(self):
        y, x, theta = self._experiment.estimator.get_position()
        scale = self._experiment.calibrator.mm_px ** 2

        # try:
        #     t, motor_pos = self._experiment.acc_motor.data_queue.get()
        # except:
        #     pass
        return (not np.isnan(x)) and True

    def check_condition_off(self):
        y, x, theta = self._experiment.estimator.get_position()
        scale = self._experiment.calibrator.mm_px ** 2
        return np.isnan(x) or False

    def paint(self, p, w, h):
        super().paint(p, w, h)
