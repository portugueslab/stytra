import numpy as np
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QApplication
import qimage2ndarray
from stytra.stimulation.stimuli import *


class GLStimDisplay(QOpenGLWidget):
    def __init__(self, protocol, *args):
        super().__init__(*args)
        self.img = None
        self.calibrating = False
        self.calibration = None
        self.dims = None

        self.protocol = protocol
        protocol.sig_timestep.connect(self.display_stimulus)

    def setImage(self, img=None):
        if img is not None:
            self.img = qimage2ndarray.array2qimage(img)
        else:
            self.img = None

    def paintEvent(self, QPaintEvent):
        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        w = self.width()
        h = self.height()
        p.drawRect(QRect(-1, -1, w+2, h+2))
        if self.calibrating and self.calibration is not None:
            self.calibration.make_calibration_pattern(p, h, w)

        p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
        if self.img is not None:
            p.drawImage(QPoint(0, 0), self.img)

    def display_stimulus(self, i_stim):
        self.dims = (self.height(), self.width())

        if isinstance(self.protocol.current_stimulus, ImageStimulus):
            self.setImage(self.protocol.current_stimulus.get_image())
        elif isinstance(self.protocol.current_stimulus, PainterStimulus):
            p = QPainter(self)
            self.protocol.current_stimulus.paint(p)
        self.update()
