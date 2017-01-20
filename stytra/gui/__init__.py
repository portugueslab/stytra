import numpy as np
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QApplication
import qimage2ndarray


class GLStimDisplay(QOpenGLWidget):
    def __init__(self, *args):
        super().__init__(*args)
        self.img = None
        self.calibrating = True


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


class StimulusDisplayWindow(QDialog):
    def __init__(self, stimuli, window_geom=(100, 100, 600, 600), *args):
        """ Class for fast scrolling through sequence of images and viewing
        associated data

        """
        super(StimulusDisplayWindow, self).__init__(*args)
        self.widget_display = GLStimDisplay(self)
        self.widget_display.setMaximumSize(2000, 2000)
        self.widget_display.setGeometry(*window_geom)

        self.refresh_rate = 1

        self.loc = np.array((0, 0))
        self.dims = (self.widget_display.height(), self.widget_display.width())

        self.setStyleSheet('background-color:black;')

        self.stimuli = stimuli

        for stimulus in self.stimuli:
            stimulus.output_shape = self.dims

    def get_current_dims(self):
        self.dims = (self.widget_display.height(), self.widget_display.width())
        return self.dims

    def set_dims(self, box):
        self.widget_display.setGeometry(
            *([int(k) for k in box.pos()] +
              [int(k) for k in box.size()]))

        self.dims = (self.widget_display.height(), self.widget_display.width())
        for stimulus in self.stimuli:
            stimulus.output_shape = self.dims

    #def update_dims(self):
    #    self.dims = (self.widget_display.height(), self.widget_display.width())
    #    for stimulus in self.stimuli:
    #        stimulus.output_shape = self.dims

    def display_stimulus(self, i_stim):
        if i_stim < 0 or i_stim >= len(self.stimuli):
            self.widget_display.setImage(
                qimage2ndarray.gray2qimage(np.zeros(self.dims)))
        else:
            print('sonovivo')
            self.widget_display.setImage(self.stimuli[i_stim].get_image())
        self.widget_display.update()



