from PyQt5.QtCore import QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QBrush, QColor, QImage, QPixmap
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QWidget
from datetime import datetime
from stytra.stimulation.stimuli import PainterStimulus
from stytra.collectors import HasPyQtGraphParams
import numpy as np
import qimage2ndarray



class StimulusDisplayWindow(QDialog, HasPyQtGraphParams):
    def __init__(self, protocol_runner, calibrator, **kwargs):
        """ Make a display window for a visual simulation protocol,
        with a display area that can be controlled and changed from a ProtocolControlWindow
        """
        super().__init__(name='stimulus_display_params', **kwargs)
        self.setWindowTitle('Stytra stimulus display')
        self.widget_display = GLStimDisplay(self,
                                            protocol_runner=protocol_runner,
                                            calibrator=calibrator)
        self.widget_display.setMaximumSize(2000, 2000)

        # self.params.setName()
        self.params.addChildren([{'name': 'pos', 'value': (0, 0),
                                  'visible': False},
                                 {'name': 'size', 'value': (400, 400),
                                  'visible': False}])

        self.setStyleSheet('background-color:black;')
        self.params.sigTreeStateChanged.connect(self.set_dims)

    def set_dims(self):
        self.widget_display.setGeometry(*(self.params['pos']+self.params['size']))

    def set_protocol(self, protocol):
        self.widget_display.set_protocol_runner(protocol)



class GLStimDisplay(QWidget):
    def __init__(self,  *args, protocol_runner, calibrator):
        super().__init__(*args)
        self.img = None
        self.calibrating = False
        self.calibrator = calibrator
        self.dims = None

        # storing of displayed frames
        self.store_frames = False
        self.stored_frames = []

        self.protocol_runner = protocol_runner
        self.protocol_runner.sig_timestep.connect(self.display_stimulus)

        self.current_time = datetime.now()
        self.starting_time = datetime.now()

        self.k = 0

        self.movie = []

    def paintEvent(self, QPaintEvent):
        self.new_img = QImage()
        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        w = self.width()
        h = self.height()

        if self.protocol_runner is not None and \
                isinstance(self.protocol_runner.current_stimulus, PainterStimulus):
            self.protocol_runner.current_stimulus.paint(p, w, h)

        else:
            p.drawRect(QRect(-1, -1, w+2, h+2))
            p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
            if self.img is not None:
                p.drawImage(QPoint(0, 0), self.img)

        if self.calibrator is not None and self.calibrator.enabled:
            self.calibrator.make_calibration_pattern(p, h, w)

        p.end()

    def display_stimulus(self):

        self.dims = (self.height(), self.width())
        self.update()
        if self.store_frames:

            self.render()

        self.k += 1
        if self.k == 10:
            a = self.grab()
            arr = qimage2ndarray.recarray_view(a.toImage())
            self.movie.append(arr['r'])
            self.k = 0

    def get_movie(self):
        movie_arr = np.array(self.movie)
        self.movie = []

        return movie_arr

