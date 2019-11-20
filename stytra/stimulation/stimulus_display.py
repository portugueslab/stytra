from datetime import datetime

import numpy as np
import qimage2ndarray
from PyQt5.QtCore import QPoint, QRect, Qt, QSize
from PyQt5.QtGui import QPainter, QBrush, QColor, QTransform
from PyQt5.QtWidgets import (
    QOpenGLWidget,
    QWidget,
    QDockWidget,
    QPushButton,
    QVBoxLayout,
    QSizePolicy,
)

from lightparam.param_qt import ParametrizedWidget, Param


class StimulusDisplayWindow(ParametrizedWidget):
    """Display window for a visual simulation protocol,
    with a display area that can be controlled and changed from a
    ProtocolControlWindow.
    
    The display area (either a QWidget or a QOpenGLWidget, see below)
    is where the paint() method of  the current Stimulus will draw
    the current image. The paint() method is called in the paintEvent() of
    the QWidget.
    
    Stimuli sequence and its timing is handled via a linked ProtocolRunner
    object.
    
    Information about real dimensions of the display comes from a
    calibrator object.
    
    If required, a movie of the displayed stimulus can be acquired and saved.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        protocol_runner,
        calibrator,
        record_stim_framerate=None,
        gl=False,
        **kwargs
    ):
        """
        :param protocol_runner: ProtocolRunner object that handles the stim
        sequence.
        :param calibrator: Calibrator object
        :param record_stim_framerate: either None or the framerate at which
         the stimulus is to be recorded
        """
        super().__init__(
            name="stimulus/display_params", tree=protocol_runner.experiment.dc, **kwargs
        )
        self.setWindowTitle("Stytra stimulus display")

        # QOpenGLWidget is faster in painting complicated stimuli (but slower
        # with easy ones!) but does not allow stimulus recording. Therefore,
        # parent class for the StimDisplay window is created at runtime:

        if record_stim_framerate is not None or not gl:
            QWidgetClass = QWidget
        else:
            QWidgetClass = QOpenGLWidget

        StimDisplay = type("StimDisplay", (StimDisplayWidget, QWidgetClass), {})
        self.widget_display = StimDisplay(
            self,
            calibrator=calibrator,
            protocol_runner=protocol_runner,
            record_stim_framerate=record_stim_framerate,
        )
        self.widget_display.setMaximumSize(2000, 2000)

        self.pos = Param((0, 0))
        self.size = Param((400, 400))

        self.setStyleSheet("background-color:black;")
        self.sig_param_changed.connect(self.set_dims)
        self.set_dims()

    def set_dims(self):
        """ Set monitor dimensions when changed from the control GUI.
        """
        self.widget_display.setGeometry(*(tuple(self.pos) + tuple(self.size)))


class StimulusDisplayOnMainWindow(QWidget):
    """ Widget for stimulus display on the main GUI window."""

    def __init__(self, experiment, **kwargs):

        super().__init__(**kwargs)
        self.experiment = experiment
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        StimDisplay = type("StimDisplay", (StimDisplayWidgetConditional, QWidget), {})
        self.widget_display = StimDisplay(
            self,
            calibrator=self.experiment.calibrator,
            protocol_runner=self.experiment.protocol_runner,
            record_stim_framerate=None,
        )

        self.layout_inner = QVBoxLayout()
        self.layout_inner.addWidget(self.widget_display)
        self.button_show_display = QPushButton(
            "Show stimulus (showing stimulus may impair performance)"
        )
        self.widget_display.display_state = False
        self.button_show_display.clicked.connect(self.change_button)
        self.layout_inner.addWidget(self.button_show_display)

        self.layout_inner.setContentsMargins(12, 0, 12, 12)
        self.container_layout.addLayout(self.layout_inner)
        self.setLayout(self.container_layout)
        self.container_layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.widget_display.sizeHint = lambda: QSize(100, 100)
        sizePolicy = QSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding
        )
        self.widget_display.setSizePolicy(sizePolicy)

        self.widget_display.setMaximumSize(500, 500)

    def change_button(self):
        """ """
        if self.widget_display.display_state:
            self.button_show_display.setText("Show stimulus (may impair performance!)")
            self.button_show_display.setStyleSheet("background-color: None")
            self.widget_display.display_state = False
        else:
            self.button_show_display.setText("Pause (pause not to impair performance!)")
            self.button_show_display.setStyleSheet("background-color: rgb(170, 30, 0)")
            self.widget_display.display_state = True


class StimDisplayWidget:
    """Widget for the actual display area contained inside the
    StimulusDisplayWindow.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, protocol_runner, calibrator, record_stim_framerate):
        """
        Check ProtocolControlWindow __init__ documentation for description
        of arguments.
        """
        super().__init__(*args)

        self.calibrator = calibrator
        self.protocol_runner = protocol_runner
        self.record_stim_framerate = record_stim_framerate

        self.img = None
        self.calibrating = False
        self.dims = None

        # storing of displayed frames
        self.k = 0
        if record_stim_framerate is None:
            self.stored_frames = None
        else:
            self.stored_frames = []

        # Connect protocol_runner timer to stimulus updating function:
        self.protocol_runner.sig_timestep.connect(self.display_stimulus)

        self.k = 0
        self.starting_time = None
        self.last_time = self.starting_time

        self.movie = []
        self.movie_timestamps = []

    def paintEvent(self, QPaintEvent):
        """Generate the stimulus that will be displayed. A QPainter object is
        defined, which is then passed to the current stimulus paint function
        for drawing the stimulus.

        Parameters
        ----------
        QPaintEvent :
            

        Returns
        -------

        """
        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        w = self.width()
        h = self.height()

        if self.protocol_runner is not None:
            if self.protocol_runner.running:
                try:
                    self.protocol_runner.current_stimulus.paint(p, w, h)
                except AttributeError:
                    pass
            else:
                p.drawRect(QRect(-1, -1, w + 2, h + 2))
                p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
                if self.img is not None:
                    p.drawImage(QPoint(0, 0), self.img)

        if self.calibrator is not None:
            if self.calibrator.enabled:
                self.calibrator.paint_calibration_pattern(p, h, w)

        p.end()

    def display_stimulus(self):
        """Function called by the protocol_runner timestep timer that update
        the displayed image and, if required, grab a picture of the current
        widget state for recording the stimulus movie. """
        self.update()
        current_time = datetime.now()

        # Grab frame if recording is enabled.
        if self.starting_time is None:
            self.starting_time = current_time

        if self.record_stim_framerate:
            now = datetime.now()
            # Only one every self.record_stim_every frames will be captured.
            if (
                self.last_time is None
                or (now - self.last_time).total_seconds()
                >= 1 / self.record_stim_framerate
            ):
                #
                # QImage from QPixmap taken with QWidget.grab():
                img = self.grab().toImage()
                arr = qimage2ndarray.rgb_view(img)  # Convert to np array
                self.movie.append(arr.copy())
                self.movie_timestamps.append(
                    (current_time - self.starting_time).total_seconds()
                )

                self.last_time = current_time

    def get_movie(self):
        """Finalize stimulus movie.
        :return: a channel x time x N x M  array with stimulus movie

        Parameters
        ----------

        Returns
        -------

        """
        if self.record_stim_framerate is not None:
            movie_arr = self.movie

            movie_timestamps = np.array(self.movie_timestamps)
            return movie_arr, movie_timestamps

        else:
            return None, None

    def reset(self):
        """ Resets the movie recorder

        Returns
        -------

        """
        self.movie = []
        self.movie_timestamps = []
        self.starting_time = None


class StimDisplayWidgetConditional(StimDisplayWidget):
    def __init__(self, *args, protocol_runner, calibrator, record_stim_framerate):
        super().__init__(
            *args,
            protocol_runner=protocol_runner,
            calibrator=calibrator,
            record_stim_framerate=record_stim_framerate
        )
        self.button_show_state = True

    def display_stimulus(self):

        if self.display_state:
            self.update()
        current_time = datetime.now()

        # Grab frame if recording is enabled.
        if self.starting_time is None:
            self.starting_time = current_time

        if self.record_stim_framerate:
            now = datetime.now()
            # Only one every self.record_stim_every frames will be captured.
            if (
                self.last_time is None
                or (now - self.last_time).total_seconds()
                >= 1 / self.record_stim_framerate
            ):
                #
                # QImage from QPixmap taken with QWidget.grab():
                img = self.grab().toImage()
                arr = qimage2ndarray.rgb_view(img)  # Convert to np array
                self.movie.append(arr.copy())
                self.movie_timestamps.append(
                    (current_time - self.starting_time).total_seconds()
                )

                self.last_time = current_time

    def paintEvent(self, QPaintEvent):

        p = QPainter(self)
        p.setBrush(QBrush(QColor(0, 0, 0)))

        w = self.width()
        h = self.height()

        if self.display_state:

            if self.protocol_runner is not None:
                if self.protocol_runner.running:
                    try:
                        self.protocol_runner.current_stimulus.paint(p, w, h)
                    except AttributeError:
                        pass
                else:
                    p.drawRect(QRect(-1, -1, w + 2, h + 2))
                    p.setRenderHint(QPainter.SmoothPixmapTransform, 1)
                    if self.img is not None:
                        p.drawImage(QPoint(0, 0), self.img)

            if self.calibrator is not None:
                if self.calibrator.enabled:
                    self.calibrator.paint_calibration_pattern(p, h, w)

        p.end()
