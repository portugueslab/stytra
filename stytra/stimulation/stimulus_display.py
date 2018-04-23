from PyQt5.QtCore import QPoint, QRect, QSize
from PyQt5.QtGui import QPainter, QBrush, QColor, QImage, QPixmap
from PyQt5.QtWidgets import QDialog, QOpenGLWidget, QWidget
from datetime import datetime
from stytra.stimulation.stimuli import PainterStimulus
from stytra.data_log import HasPyQtGraphParams
import numpy as np
import qimage2ndarray



# TODO this entire module should be moved to the stimulation
class StimulusDisplayWindow(QDialog, HasPyQtGraphParams):
    """ Make a display window for a visual simulation protocol,
    with a display area that can be controlled and changed from a
    ProtocolControlWindow.
    """
    def __init__(self, protocol_runner, calibrator,
                 record_stim_every=10, **kwargs):
        """
        :param protocol_runner:
        :param calibrator:
        :param record_stim_every:
        """
        super().__init__(name='stimulus_display_params', **kwargs)
        self.setWindowTitle('Stytra stimulus display')

        # QOpenGLWidget is faster in painting complicated stimuli (but slower
        # with easy ones!) but does not allow stimulus recording. Therefore,
        # parent class for the StimDisplay window is created at runtime:

        if record_stim_every is not None:
            QWidgetClass = QWidget
        else:
            QWidgetClass = QOpenGLWidget

        StimDisplay = type('StimDisplay', (GLStimDisplay, QWidgetClass), {})
        self.widget_display = StimDisplay(self, calibrator=calibrator,
                                                protocol_runner=protocol_runner,
                                                record_stim_every=record_stim_every)
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


class GLStimDisplay():
    """ Widget for the actual display area contained inside the
    StimulusDisplayWindow.
    """

    def __init__(self, *args, protocol_runner, calibrator, record_stim_every):
        """ Check ProtocolControlWindow __init__ documentation for description
        of arguments.
        """
        super().__init__(*args)

        self.calibrator = calibrator
        self.protocol_runner = protocol_runner
        self.record_stim_every = record_stim_every

        self.img = None
        self.calibrating = False
        self.dims = None

        # storing of displayed frames
        self.stored_frames = None
        self.k = 0
        if record_stim_every is not None:
            self.stored_frames = []

        # Connect protocol_runner timer to stimulus updating function:
        self.protocol_runner.sig_timestep.connect(self.display_stimulus)

        self.k = 0
        self.starting_time = datetime.now()

        self.movie = []
        self.movie_timestamps = []

    def paintEvent(self, QPaintEvent):
        """ Generate the stimulus that will be displayed. A QPainter object is
        defined, which is then passed to the current stimulus paint function
        for drawing the stimulus.
        """
        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        w = self.width()
        h = self.height()
        if self.calibrator is not None and self.calibrator.enabled:
            self.calibrator.make_calibration_pattern(p, h, w)
        else:
            if self.protocol_runner is not None and \
                    isinstance(self.protocol_runner.current_stimulus, PainterStimulus):
                if self.protocol_runner.running:
                    self.protocol_runner.current_stimulus.paint(p, w, h)
            else:
                p.drawRect(QRect(-1, -1, w+2, h+2))
                p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
                if self.img is not None:
                    p.drawImage(QPoint(0, 0), self.img)

        p.end()

    def display_stimulus(self):
        """ Function called by the protocol_runner timestep timer that update
        the displayed image and, if required, grab a picture of the current
        widget state for recording the stimulus movie.
        """

        self.dims = (self.height(), self.width())  # Update dimensions
        self.update()  # update image

        # Grab frame if recording is enabled.
        if self.record_stim_every is not None:
            self.k += 1
            # Only one every self.record_stim_every frames will be captured.
            if np.mod(self.k, self.record_stim_every) == 0:
                #
                # QImage from QPixmap taken with QWidget.grab():
                img = self.grab().toImage()
                arr = qimage2ndarray.recarray_view(img)  # Convert to np array
                self.movie.append(np.array([arr[k] for k in ['r', 'g', 'b']]))
                self.movie_timestamps.append(
                    (datetime.now() - self.starting_time).total_seconds())

                self.k = 0

    def get_movie(self):
        """ Finalize stimulus movie.
        :return: a channel x time x N x M  array with stimulus movie
        """
        if self.record_stim_every is not None:
            movie_arr = np.array(self.movie)
            movie_arr = movie_arr.swapaxes(1, 3)

            movie_timestamps = np.array(self.movie_timestamps)
            self.movie = []
            self.movie_timestamps = []
            return movie_arr, movie_timestamps

        else:
            return None

