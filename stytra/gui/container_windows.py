import logging
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QSplitter,
    QDockWidget,
)

from pyqtgraph.parametertree import ParameterTree

from stytra.gui.extra_widgets import CollapsibleWidget
from stytra.gui.monitor_control import ProjectorAndCalibrationWidget
from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.protocol_control import ProtocolControlWidget
from stytra.gui.camera_display import (
    CameraViewWidget,
    CameraEmbeddedTrackingSelection,
    CameraViewFish,
)

from lightparam.gui import ParameterGui

import json


class QPlainTextEditLogger(logging.Handler):
    def __init__(self):
        super().__init__()
        self.widget = QPlainTextEdit()
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = "{} {}".format(
            datetime.datetime.now().strftime("[%H:%M:%S]"), self.format(record)
        )
        self.widget.appendPlainText(msg)


class DebugLabel(QLabel):
    """ """

    def __init__(self, *args, debug_on=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border-radius: 2px")
        self.set_debug(debug_on)
        self.setMinimumHeight(36)

    def set_debug(self, debug_on=False):
        """

        Parameters
        ----------
        debug_on :
             (Default value = False)

        Returns
        -------

        """
        if debug_on:
            self.setText("Debug mode is on, data will not be saved!")
            self.setStyleSheet("background-color: #dc322f;color:#fff")
        else:
            self.setText("Experiment ready, please ensure the data_log is correct")
            self.setStyleSheet("background-color: #002b36")


class SimpleExperimentWindow(QMainWindow):
    """Window for controlling a simple experiment including only a monitor
    the relative controls and the buttons for data_log and protocol control.

    Parameters
    ----------
    experiment : `Experiment <stytra.experiments.Experiment>` object
        experiment for which the window is built.

    Returns
    -------

    """

    def __init__(self, experiment, **kwargs):
        """ """
        super().__init__(**kwargs)
        self.experiment = experiment

        self.setWindowTitle("Stytra")

        # self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        if not self.experiment.offline:
            self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        self.widget_control = ProtocolControlWidget(experiment.protocol_runner)

        # Connect signals from the protocol_control:
        self.widget_control.sig_start_protocol.connect(experiment.start_protocol)
        self.widget_control.sig_stop_protocol.connect(experiment.end_protocol)
        self.button_metadata = QPushButton("Edit metadata")

        if experiment.trigger is not None:
            self.chk_scope = QCheckBox("Wait for trigger signal")
        self.button_metadata.clicked.connect(self.show_metadata_gui)

        self.logger = QPlainTextEditLogger()
        self.experiment.logger.addHandler(self.logger)

        self.setCentralWidget(self.construct_ui())

        self.metadata_win = None

    def show_metadata_gui(self):
        """ """
        self.metadata_win = QWidget()
        self.metadata_win.setLayout(QHBoxLayout())
        self.metadata_win.layout().addWidget(
            ParameterGui(self.experiment.metadata)
        )
        self.metadata_win.layout().addWidget(
            ParameterGui(self.experiment.metadata_animal)
        )
        self.metadata_win.show()

    def construct_ui(self):
        """ """
        central_widget = QWidget()
        protocol_layout = QVBoxLayout()
        # central_widget.layout().addWidget(self.label_debug)
        if not self.experiment.offline:
            protocol_layout.addWidget(
                CollapsibleWidget(self.widget_projection, "Projector setup")
            )
        protocol_layout.addWidget(
            CollapsibleWidget(self.logger.widget, "Log", expanded=False)
        )
        protocol_layout.addWidget(self.widget_control)
        if self.experiment.trigger is not None:
            protocol_layout.addWidget(self.chk_scope)
        protocol_layout.addWidget(self.button_metadata)

        central_layout = QHBoxLayout()
        central_layout.addLayout(protocol_layout)
        central_widget.setLayout(central_layout)
        return central_widget

    def write_log(self, msg):
        self.log_widget.textCursor().appendPlainText(msg)

    def closeEvent(self, *args, **kwargs):
        """

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        self.experiment.wrap_up()


class CameraExperimentWindow(SimpleExperimentWindow):
    """ """

    def __init__(self, *args, **kwargs):
        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.camera_display = CameraViewWidget(kwargs["experiment"])
        self.plot_framerate = MultiStreamPlot(time_past=5, round_bounds=10)

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        previous_widget = super().construct_ui()
        previous_widget.layout().addWidget(self.plot_framerate)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(previous_widget)
        return self.camera_splitter


class DynamicStimExperimentWindow(SimpleExperimentWindow):
    """Window for plotting a dynamically varying stimulus.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, **kwargs):

        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        time_past = 30
        self.stream_plot = MultiStreamPlot(time_past=time_past)
        self.monitoring_layout.addWidget(self.stream_plot)

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        previous_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        return self.monitoring_widget


class TrackingExperimentWindow(SimpleExperimentWindow):
    """Window for controlling an experiment where the tail of an
    embedded fish is tracked.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self, tracking=True, tail=False, eyes=False, fish=False, *args, **kwargs
    ):
        # TODO refactor movement detection
        self.tracking = tracking
        self.tail = tail
        self.eyes = eyes
        self.fish = fish

        if fish:
            self.camera_display = CameraViewFish(experiment=kwargs["experiment"])
        elif tail or eyes:
            self.camera_display = CameraEmbeddedTrackingSelection(
                experiment=kwargs["experiment"], tail=tail, eyes=eyes
            )
        else:
            self.camera_display = CameraViewWidget(experiment=kwargs["experiment"])

        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)

        self.layout_track_btns = QHBoxLayout()
        self.layout_track_btns.setContentsMargins(0,0,0,0)

        # Tracking params button:
        self.button_tracking_params = QPushButton(
            "Tracking params"
            if (self.tail or self.eyes or self.fish)
            else "Movement detection params"
        )

        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)

        self.button_save_tracking_params = QPushButton("Save parameters")
        self.button_save_tracking_params.clicked.connect(self.save_tracking_params)

        self.layout_track_btns.addWidget(self.button_tracking_params)
        self.layout_track_btns.addWidget(self.button_save_tracking_params)

        self.monitoring_layout.addLayout(self.layout_track_btns)

        self.track_params_wnd = None

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        previous_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(self.monitoring_widget)
        return self.camera_splitter

    def open_tracking_params_tree(self):
        """ """
        self.track_params_wnd = QWidget()
        self.track_params_wnd.setLayout(QVBoxLayout())
        if hasattr(self.experiment, "tracking_method"):
            self.track_params_wnd.layout().addWidget(QLabel("Tracking method"))
            self.track_params_wnd.layout().addWidget(ParameterGui(self.experiment.tracking_method.params))
        if (
            hasattr(self.experiment, "preprocessing_method")
            and self.experiment.preprocessing_method is not None
        ):
            self.track_params_wnd.layout().addWidget(QLabel("Preprocessing method"))
            self.track_params_wnd.addParameters(
                self.track_params_wnd.layout().addWidget(
                    ParameterGui(self.experiment.preprocessing_method.params))
            )
        if hasattr(self.experiment, "motion_detection_params"):
            self.track_params_wnd.layout().addWidget(QLabel("Motion detection"))
            self.track_params_wnd.layout().addWidget(
                ParameterGui(self.experiment.motion_detection_params))
        self.track_params_wnd.setWindowTitle("Tracking parameters")

        self.track_params_wnd.show()

    def save_tracking_params(self):
        json.dump(self.experiment.tracking_method.get_clean_values,
                  open(self.experiment.filename_base() + "tracking_params.json"))


class VRExperimentWindow(SimpleExperimentWindow):
    """ """

    def reconfigure_ui(self):
        """ """
        self.main_layout = QSplitter()
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.positionPlot = StreamingPositionPlot(
            data_accumulator=self.protocol.dynamic_log
        )
        self.monitoring_layout.addWidget(self.positionPlot)
        self.gui_refresh_timer.timeout.connect(self.positionPlot.update)

        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)

        self.stream_plot.add_stream(
            self.experiment.data_acc_tailpoints, ["tail_sum", "theta_01"]
        )

        self.stream_plot.add_stream(
            self.experiment.estimator.log,
            ["v_ax", "v_lat", "v_ang", "middle_tail", "indexes_from_past_end"],
        )

        self.main_layout.addWidget(self.monitoring_widget)
        self.main_layout.addWidget(self.controls_widget)
        self.setCentralWidget(self.main_layout)
