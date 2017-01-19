import numpy as np
from PyQt5.QtGui import QImage


class Stimulus:
    """ General class for a stimulus."""
    def __init__(self, output_shape=(100, 100), duration=0.0):
        self.started = None
        self.elapsed = 0.0
        self.duration = duration
        self.output_shape = output_shape
        self.name = ''

    def state(self):
        """ Returns a dictionary with stimulus features """
        return dict(name=self.name)

    def update(self):
        pass

    def get_image(self):
        pass


class Flash(Stimulus):
    """ Flash stimulus """
    def __init__(self, *args, color=(255, 255, 255), **kwargs):
        super(Flash, self).__init__(*args, **kwargs)
        self.color = color
        self.name = 'Whole field'
        self.imdata = np.ones(self.output_shape + (3,), dtype=np.uint8) * \
                np.array(self.color, dtype=np.uint8)[None, None, :]


    def get_image(self):
        return QImage(self.imdata.data, self.imdata.shape[1],
                      self.imdata.shape[0],
                      self.imdata.strides[0], QImage.Format_RGB888)

    def state(self):
        state_dict = super(Flash, self).state()
        state_dict.update({'color': self.color,
                           'random_feature': 1})

        return state_dict


class Pause(Flash):
    def __init__(self, *args, **kwargs):
        super(Pause, self).__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'Pause'

class DynamicStimulus(Stimulus):
    pass

class ClosedLoopStimulus(DynamicStimulus):
    pass


class ClosedLoop1D(DynamicStimulus):
    def update(self):
        pass