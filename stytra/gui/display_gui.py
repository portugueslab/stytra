import numpy as np
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QDialog
from stytra.gui import GLStimDisplay


class StimulusDisplayWindow(QDialog):
    def __init__(self, protocol, *args):
        """ Make a display window for a visual simulation protocol,
        with a movable display area

        """
        super().__init__(*args)

        self.protocol = protocol
        self.widget_display = GLStimDisplay(protocol, self)
        self.widget_display.setMaximumSize(2000, 2000)
        self.display_params = dict(window=dict(pos=(0,0), size=(100,100)),
                                   refresh_rate=1/60.)

        self.update_display_params()
        self.loc = np.array((0, 0))
        self.dims = (self.widget_display.height(), self.widget_display.width())

        self.setStyleSheet('background-color:black;')

    def update_display_params(self):
        self.set_dims(**self.display_params['window'])
        self.protocol.dt = self.display_params['refresh_rate']

    def get_current_dims(self):
        self.dims = (self.widget_display.height(), self.widget_display.width())
        return self.dims

    def set_dims(self, pos, size):
        self.widget_display.setGeometry(
            *([int(k) for k in pos] +
              [int(k) for k in size]))

        self.dims = (self.widget_display.height(), self.widget_display.width())
        for stimulus in self.protocol.stimuli:
            stimulus.output_shape = self.dims