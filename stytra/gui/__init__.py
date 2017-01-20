import numpy as np
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QApplication
import qimage2ndarray


class GLStimDisplay(QOpenGLWidget):
    def __init__(self, protocol, *args):
        super().__init__(*args)
        self.img = None
        self.calibrating = True

        self.protocol = protocol
        protocol.sig_timestep.connect(self.display_stimulus)


    def setImage(self, img):
        self.img = img

    def calibrate(self):
        p = QPainter(self)
        p.drawLine()

    def paintEvent(self, QPaintEvent):
        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        w = self.width()
        h = self.height()
        p.drawRect(QRect(-1, -1, w+2, h+2))
        if self.calibrating:
            p.setPen(QPen(QColor(255, 0, 0)))
            p.drawRect(QRect(1, 1, w-2, h-2))
            p.drawLine(w//4, h//2, w*3//4, h//2)
            p.drawLine(w // 2, h *3 // 4, w // 2, h // 4)
            p.drawLine(w // 2, h * 3 // 4, w // 2, h // 4)
            p.drawLine(w //2, h*3//4, w*3//4, h*3//4)

        p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
        if self.img is not None:
            p.drawImage(QPoint(0, 0), self.img)

    def display_stimulus(self, i_stim):
        self.dims = (self.height(), self.width())

        if i_stim < 0 or i_stim >= len(self.protocol.stimuli):
            self.setImage(
                qimage2ndarray.gray2qimage(np.zeros(self.dims)))
        else:
            self.setImage(self.protocol.stimuli[i_stim].get_image())
        self.update()

