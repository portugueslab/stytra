import numpy as np
from PyQt5.QtGui import QImage
import qimage2ndarray
from PyQt5.QtGui import QPainter, QImage
from PyQt5.QtCore import QPoint
import cv2


class Stimulus:
    """ General class for a stimulus."""
    def __init__(self, output_shape=(100, 100), duration=0.0):
        """ Make a stimulus, with the basic properties common to all stimuli
        Initial values which do not change during the stimulus
        are prefixed with _, so that they are not logged
        at every time step


        :param output_shape:
        :param duration:
        """
        self._started = None
        self.elapsed = 0.0
        self.duration = duration
        self.output_shape = output_shape
        self.name = ''

    def get_state(self):
        """ Returns a dictionary with stimulus features """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != '_':
                state_dict[key] = value

        return state_dict

    def update(self):
        pass


class ImageStimulus(Stimulus):
    def get_image(self):
        pass


class Flash(ImageStimulus):
    """ Flash stimulus """
    def __init__(self, *args, color=(255, 255, 255), **kwargs):
        super(Flash, self).__init__(*args, **kwargs)
        self.color = color
        self.name = 'Whole field'
        self._imdata = np.ones(self.output_shape + (3,), dtype=np.uint8) * \
                       np.array(self.color, dtype=np.uint8)[None, None, :]


    def get_image(self):
        self._imdata = np.ones(self.output_shape + (3,), dtype=np.uint8) * \
                       np.array(self.color, dtype=np.uint8)[None, None, :]

        return self._imdata

    def state(self):
        # Add flash features to general properties dictionary:
        return dict(super(Flash, self).state(),
                    color=self.color)


class Pause(Flash):
    def __init__(self, *args, **kwargs):
        super(Pause, self).__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'Pause'


class PainterStimulus(Stimulus):
    def paint(self, p):
        pass


class SeamlessStimulus(ImageStimulus):
    def __init__(self, *args, background=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = 0
        self.y = 0
        self.theta = 0
        self._background = background

    def _transform_mat(self):
        if self.theta == 0:
            return np.array([[1, 0, self.y],
                             [0, 1, self.x]]).astype(np.float32)
        else:
            return np.array([[np.cos(self.theta), -np.sin(self.theta), self.y],
                             [np.sin(self.theta), np.cos(self.theta), self.x]]).astype(np.float32)

    def get_image(self):
        self.update()
        to_display = cv2.warpAffine(self._background, self._transform_mat(),
                                    borderMode=cv2.BORDER_WRAP,
                                    dsize=self.output_shape)
        return to_display


class MovingSeamless(SeamlessStimulus):
    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion

    def update(self):
        self.x = np.interp(self.elapsed, self.motion.t, self.motion.x)
        self.y = np.interp(self.elapsed, self.motion.t, self.motion.y)


class DynamicStimulus(Stimulus):
    pass


class ClosedLoopStimulus(DynamicStimulus):
    pass


class ClosedLoop1D(DynamicStimulus):
    def update(self):
        pass