import numpy as np
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QApplication
import qimage2ndarray
from datetime import datetime
from stytra.stimulation.stimuli import ImageStimulus, PainterStimulus


class StimulusDisplayWindow(QDialog):
    def __init__(self, *args, experiment=None):
        """ Make a display window for a visual simulation protocol,
        with a movable display area

        """
        super().__init__(*args)

        self.widget_display = GLStimDisplay(self)
        self.widget_display.setMaximumSize(2000, 2000)
        self.display_params = dict(pos=(0, 0), size=(100, 100))

        self.setStyleSheet('background-color:black;')

    def set_dims(self, pos, size):
        self.widget_display.setGeometry(*(pos+size))
        self.display_params['pos'] = pos
        self.display_params['size'] = size

    def set_protocol(self, protocol):
        self.widget_display.set_protocol(protocol)


class GLStimDisplay(QOpenGLWidget):
    def __init__(self,  *args):
        super().__init__(*args)
        self.img = None
        self.calibrating = False
        self.calibrator = None
        self.dims = None

        self.protocol = None

        self.n_fps_frames = 10
        self.i_fps = 0
        self.previous_time_fps = None
        self.current_framerate = None
        self.print_framerate = True

        self.current_time = datetime.now()
        self.starting_time = datetime.now()

    def set_protocol(self, protocol):
        self.protocol = protocol
        self.protocol.sig_timestep.connect(self.display_stimulus)

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
        if self.protocol is not None and \
                isinstance(self.protocol.current_stimulus, PainterStimulus):
            self.protocol.current_stimulus.paint(p, w, h)
        else:
            p.drawRect(QRect(-1, -1, w+2, h+2))
            p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
            if self.img is not None:
                p.drawImage(QPoint(0, 0), self.img)

        if self.calibrator is not None and self.calibrator.enabled:
            self.calibrator.make_calibration_pattern(p, h, w)
        p.end()
        pass

    def display_stimulus(self):
        self.dims = (self.height(), self.width())

        if isinstance(self.protocol.current_stimulus, ImageStimulus):
            self.setImage(self.protocol.current_stimulus.get_image(self.dims))

        self.update_framerate()
        self.update()

    def update_framerate(self):
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                self.current_framerate = self.n_fps_frames / (
                    self.current_time - self.previous_time_fps).total_seconds()
                # if self.print_framerate:
                #     print('{:.2f} FPS'.format(self.current_framerate))

            self.previous_time_fps = self.current_time
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames
