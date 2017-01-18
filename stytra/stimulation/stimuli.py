import numpy as np
import qimage2ndarray
from PyQt5.QtGui import QImage

class Stimulus:
    def __init__(self, output_shape=(100, 100), duration=0.0):
        self.started = None
        self.elapsed = 0.0
        self.duration = duration
        self.output_shape = output_shape
        self.name = ''

    def state(self):
        return dict(elapsed=self.elapsed)

    def update(self):
        pass

    def get_image(self):
        pass



class Flash(Stimulus):
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


class Pause(Flash):
    def __init__(self, *args, **kwargs):
        super(Pause, self).__init__(*args, color=(0,0,0), **kwargs)


class ClosedLoopStimulus(Stimulus):
    pass


class ClosedLoop1D(ClosedLoopStimulus):
    def update(self):
        pass