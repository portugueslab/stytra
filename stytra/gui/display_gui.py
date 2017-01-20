import numpy as np
from PyQt5.QtWidgets import QDialog
from stytra.gui import GLStimDisplay


class StimulusDisplayWindow(QDialog):
    def __init__(self, protocol, window_geom=(100, 100, 600, 600), *args):
        """ Class for fast scrolling through sequence of images and viewing
        associated data

        """
        super().__init__(*args)
        self.widget_display = GLStimDisplay(protocol, self)
        self.widget_display.setMaximumSize(2000, 2000)
        self.widget_display.setGeometry(*window_geom)

        self.refresh_rate = 1

        self.loc = np.array((0, 0))
        self.dims = (self.widget_display.height(), self.widget_display.width())

        self.setStyleSheet('background-color:black;')

        self.protocol = protocol

        for stimulus in self.protocol.stimuli:
            stimulus.output_shape = self.dims

    def get_current_dims(self):
        self.dims = (self.widget_display.height(), self.widget_display.width())
        return self.dims

    def set_dims(self, box):
        self.widget_display.setGeometry(
            *([int(k) for k in box.pos()] +
              [int(k) for k in box.size()]))

        self.dims = (self.widget_display.height(), self.widget_display.width())
        for stimulus in self.protocol.stimuli:
            stimulus.output_shape = self.dims