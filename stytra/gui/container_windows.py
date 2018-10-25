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
from PyQt5.QtGui import QPalette

from lightparam.gui.collapsible_widget import CollapsibleWidget
from stytra.gui.monitor_control import ProjectorAndCalibrationWidget
from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.protocol_control import ProtocolControlToolbar
from stytra.gui.camera_display import (
    CameraViewWidget,
    CameraEmbeddedTrackingSelection,
    CameraViewFish,
)

from lightparam.gui import ParameterGui

import json

from multiprocessing import Queue
from queue import Empty


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


class StatusMessageLabel(QLabel):
    """ """

    def __init__(self, *args, debug_on=False, **kwargs):
        super().__init__(*args, **kwargs)

    def setMessage(self, text):
        if len(text) == 0:
            self.setStyleSheet("background-color: {};".format(
                self.palette().color(QPalette.Button).name()))
            self.setText("")
            return
        if text[0] == "E":
            self.setStyleSheet("background-color: #dc322f;")
        elif text[0] == "W":
            self.setStyleSheet("background-color: #d8b02d;")
        else:
            self.setStyleSheet("background-color: {};".format(
                self.palette().color(QPalette.Button).name()))
        self.setText(text[2:])


class QueueStatusMessageLabel(StatusMessageLabel):
    def __init__(self, experiment, queue: Queue):
        super().__init__()
        self.queue = queue
        experiment.gui_timer.timeout.connect(self.update_message)

    def update_message(self):
        message = ""
        while True:
            try:
                message = self.queue.get(timeout=0.0001)
            except Empty:
                break
        self.setMessage(message)


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

        self.docks = []

        # self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        if not self.experiment.offline:
            self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        self.toolbar_control = ProtocolControlToolbar(experiment.protocol_runner,
                                                      self)
        self.toolbar_control.setObjectName("toolbar")

        # Connect signals from the protocol_control:
        self.toolbar_control.sig_start_protocol.connect(experiment.start_protocol)
        self.toolbar_control.sig_stop_protocol.connect(experiment.end_protocol)

        act_metadata = self.toolbar_control.addAction("Edit metadata")
        act_metadata.triggered.connect(self.show_metadata_gui)

        if experiment.trigger is not None:
            self.chk_scope = QCheckBox("Wait for trigger signal")

        self.logger = QPlainTextEditLogger()
        self.experiment.logger.addHandler(self.logger)

        if self.experiment.database is not None:
            self.status_db = StatusMessageLabel()
            self.statusBar().addWidget(self.status_db)

        self.status_metadata = StatusMessageLabel()
        self.statusBar().addWidget(self.status_metadata)

        self.metadata_win = None

    def show_metadata_gui(self):
        """ """
        self.metadata_win = QWidget()
        self.metadata_win.setLayout(QHBoxLayout())
        self.metadata_win.layout().addWidget(ParameterGui(self.experiment.metadata))
        self.metadata_win.layout().addWidget(
            ParameterGui(self.experiment.metadata_animal)
        )
        self.metadata_win.show()

    def construct_ui(self):
        """ """
        self.addToolBar(Qt.TopToolBarArea, self.toolbar_control)

        if not self.experiment.offline:
            proj_dock = QDockWidget("Projector configuration", self)
            proj_dock.setWidget(self.widget_projection)
            proj_dock.setObjectName("dock_projector")
            self.docks.append(proj_dock)
            self.addDockWidget(Qt.RightDockWidgetArea, proj_dock)

        log_dock = QDockWidget("Log", self)
        log_dock.setObjectName("dock_log")
        log_dock.setWidget(self.logger.widget)
        self.docks.append(log_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, log_dock)

        if self.experiment.trigger is not None:
            self.toolbar_control.addWidget(self.chk_scope)

        self.toolbar_control.setObjectName("toolbar_control")
        self.setCentralWidget(None)
        return None

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

    def __init__(self, fish=False, tail=False, eyes=False, **kwargs):
        super().__init__(**kwargs)

        if fish:
            self.camera_display = CameraViewFish(experiment=kwargs["experiment"])
        elif tail or eyes:
            self.camera_display = CameraEmbeddedTrackingSelection(
                experiment=kwargs["experiment"], tail=tail, eyes=eyes
            )
        else:
            self.camera_display = CameraViewWidget(experiment=kwargs["experiment"])

        self.plot_framerate = MultiStreamPlot(
            time_past=5, round_bounds=10, compact=True
        )

        self.status_camera = QueueStatusMessageLabel(
            self.experiment, self.experiment.camera.message_queue)

    def construct_ui(self):
        previous_widget = super().construct_ui()

        self.experiment.gui_timer.timeout.connect(self.plot_framerate.update)

        self.setCentralWidget(previous_widget)
        dockCamera = QDockWidget("Camera", self)
        dockCamera.setWidget(self.camera_display)
        dockCamera.setObjectName("dock_camera")

        dockFramerate = QDockWidget("Frame rates", self)
        dockFramerate.setWidget(self.plot_framerate)
        dockFramerate.setObjectName("dock_framerates")

        self.addDockWidget(Qt.LeftDockWidgetArea, dockCamera)
        self.addDockWidget(Qt.LeftDockWidgetArea, dockFramerate)
        self.docks.extend([dockCamera, dockFramerate])

        self.statusBar().insertWidget(0, self.status_camera)

        return previous_widget


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


class TrackingExperimentWindow(CameraExperimentWindow):
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
        super().__init__(*args, tail=tail, eyes=eyes, fish=fish, **kwargs)
        # TODO refactor movement detection
        self.tracking = tracking
        self.tail = tail
        self.eyes = eyes
        self.fish = fish

        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)

        self.layout_track_btns = QHBoxLayout()
        self.layout_track_btns.setContentsMargins(0, 0, 0, 0)

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

        self.status_tracking = QueueStatusMessageLabel(self.experiment,
                                                       self.experiment.frame_dispatchers[0].message_queue)

    def construct_ui(self):
        """ """
        previous_widget = super().construct_ui()
        self.experiment.gui_timer.timeout.connect(
            self.stream_plot.update
        )  # TODO put in right place
        monitoring_widget = QWidget()
        monitoring_widget.setLayout(self.monitoring_layout)
        monitoring_dock = QDockWidget("Tracking", self)
        monitoring_dock.setWidget(monitoring_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, monitoring_dock)
        self.docks.append(monitoring_dock)
        self.statusBar().insertWidget(1, self.status_tracking)
        return previous_widget

    def open_tracking_params_tree(self):
        """ """
        self.track_params_wnd = QWidget()
        self.track_params_wnd.setLayout(QVBoxLayout())
        if hasattr(self.experiment, "tracking_method"):
            self.track_params_wnd.layout().addWidget(QLabel("Tracking method"))
            self.track_params_wnd.layout().addWidget(
                ParameterGui(self.experiment.tracking_method.params)
            )
        if (
            hasattr(self.experiment, "preprocessing_method")
            and self.experiment.preprocessing_method is not None
        ):
            self.track_params_wnd.layout().addWidget(QLabel("Preprocessing method"))
            self.track_params_wnd.layout().addWidget(
                ParameterGui(self.experiment.preprocessing_method.params)
            )
        if hasattr(self.experiment, "motion_detection_params"):
            self.track_params_wnd.layout().addWidget(QLabel("Motion detection"))
            self.track_params_wnd.layout().addWidget(
                ParameterGui(self.experiment.motion_detection_params)
            )
        self.track_params_wnd.setWindowTitle("Tracking parameters")

        self.track_params_wnd.show()

    def save_tracking_params(self):
        json.dump(
            self.experiment.tracking_method.get_clean_values,
            open(self.experiment.filename_base() + "tracking_params.json"),
        )


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
