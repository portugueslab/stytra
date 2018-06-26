import logging
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QSplitter,
)
from pyqtgraph.parametertree import ParameterTree

from stytra.gui.monitor_control import ProjectorAndCalibrationWidget
from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.protocol_control import ProtocolControlWidget
from stytra.gui.camera_display import CameraViewWidget, CameraEmbeddedTrackingSelection


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


class TrackingSettingsGui(QWidget):
    """ """

    def __init__(self):
        self.combo_method = QComboBox()
        self.combo_method.set_editable(False)


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

        self.setCentralWidget(self.construct_ui())

        self.metadata_win = None

    def show_metadata_gui(self):
        """ """
        self.metadata_win = QWidget()
        self.metadata_win.setLayout(QHBoxLayout())
        self.metadata_win.layout().addWidget(
            self.experiment.metadata.show_metadata_gui()
        )
        self.metadata_win.layout().addWidget(
            self.experiment.metadata_animal.show_metadata_gui()
        )
        self.metadata_win.show()

    def construct_ui(self):
        """ """
        central_widget = QWidget()
        protocol_layout = QVBoxLayout()
        # central_widget.layout().addWidget(self.label_debug)
        protocol_layout.addWidget(self.widget_projection)
        protocol_layout.addWidget(self.widget_control)
        if self.experiment.trigger is not None:
            protocol_layout.addWidget(self.chk_scope)
        protocol_layout.addWidget(self.button_metadata)

        central_layout = QHBoxLayout()
        central_layout.addLayout(protocol_layout)
        central_layout.addWidget(self.logger.widget)
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
        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        previous_widget = super().construct_ui()
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(previous_widget)
        return self.camera_splitter


class TrackingExperimentWindow(SimpleExperimentWindow):
    """Window for controlling an experiment where the tail of an
    embedded fish is tracked.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, tracking=True, tail=False, eyes=False, *args, **kwargs):
        # TODO refactor movement detection
        self.tracking = tracking
        self.tail = tail
        self.eyes = eyes

        if tail or eyes:
            self.camera_display = CameraEmbeddedTrackingSelection(
                experiment=kwargs["experiment"], tail=tail, eyes=eyes
            )
        else:
            self.camera_display = CameraViewWidget(experiment=kwargs["experiment"])

        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        if eyes:
            time_past = 30
        else:
            time_past = 5
        self.stream_plot = MultiStreamPlot(time_past=time_past)

        self.monitoring_layout.addWidget(self.stream_plot)

        # Tracking params button:
        self.button_tracking_params = QPushButton(
            "Tracking params" if tracking else "Movement detection params"
        )
        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)
        self.monitoring_layout.addWidget(self.button_tracking_params)

        self.track_params_wnd = None

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(self.monitoring_widget)
        return self.camera_splitter

    def open_tracking_params_tree(self):
        """ """
        self.track_params_wnd = ParameterTree()
        self.track_params_wnd.setParameters(
            self.experiment.tracking_method.params, showTop=False
        )
        self.track_params_wnd.setWindowTitle("Tracking data")

        self.track_params_wnd.show()


class EyeTrackingExperimentWindow(SimpleExperimentWindow):
    """Window for controlling an experiment where the tail and the eyes
    of an embedded fish are tracked.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, **kwargs):
        self.camera_display = CameraEyesSelection(experiment=kwargs["experiment"])

        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        self.stream_plot = MultiStreamPlot(time_past=30)

        self.monitoring_layout.addWidget(self.stream_plot)

        # Tracking params button:
        self.button_tracking_params = QPushButton("Tracking params")
        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)
        self.monitoring_layout.addWidget(self.button_tracking_params)

        self.track_params_wnd = None
        # self.tracking_layout.addWidget(self.camera_display)
        # self.tracking_layout.addWidget(self.button_tracking_params)

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        """ """
        self.stream_plot.add_stream(self.experiment.data_acc, ["th_e0", "th_e1"])
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(self.monitoring_widget)
        return self.camera_splitter

    def open_tracking_params_tree(self):
        """ """
        self.track_params_wnd = ParameterTree()
        self.track_params_wnd.setParameters(
            self.experiment.tracking_method.params, showTop=False
        )
        self.track_params_wnd.setWindowTitle("Tracking data")
        self.track_params_wnd.show()


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


class LightsheetGUI(SimpleExperimentWindow):
    """ """

    def init_ui(self):
        """ """
        self.chk_lightsheet = QCheckBox("Wait for lightsheet")
        self.chk_lightsheet.setChecked(False)
