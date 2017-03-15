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

        self.setStyleSheet('background-color:black;')

    def update_display_params(self):
        self.set_dims(**self.display_params['window'])
        self.protocol.dt = self.display_params['refresh_rate']

    def set_dims(self, pos, size):
        self.widget_display.setGeometry(
            *([int(k) for k in pos] +
              [int(k) for k in size]))
        self.display_params['window']['size'] = size
        self.display_params['window']['pos'] = pos

        for stimulus in self.protocol.stimuli:
            stimulus.output_shape = tuple(int(s+1) for s in size)


