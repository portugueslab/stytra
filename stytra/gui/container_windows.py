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
    QDockWidget,
    QToolButton,
    QFileDialog,
)
from PyQt5.QtGui import QPalette, QIcon

from stytra.gui.monitor_control import ProjectorAndCalibrationWidget
from stytra.gui.plots import MultiStreamPlot, TailStreamPlot
from stytra.gui.protocol_control import ProtocolControlToolbar
from stytra.gui.camera_display import (
    CameraViewWidget,
    CameraEmbeddedTrackingSelection,
    CameraViewFish,
)
from stytra.gui.status_display import StatusMessageDisplay

from lightparam.gui import ParameterGui, pretty_name

import pkg_resources
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

        self.setWindowTitle("Stytra | "+pretty_name(type(experiment.protocol).name))

        self.docks = []

        # self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        if not self.experiment.offline:
            self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        self.toolbar_control = ProtocolControlToolbar(experiment.protocol_runner, self)
        self.toolbar_control.setObjectName("toolbar")

        # Connect signals from the protocol_control:
        self.toolbar_control.sig_start_protocol.connect(experiment.start_protocol)
        self.toolbar_control.sig_stop_protocol.connect(experiment.end_protocol)

        act_metadata = self.toolbar_control.addAction("Edit metadata")
        act_metadata.setIcon(QIcon(pkg_resources.resource_filename(__name__, "../icons/edit_fish.svg"),))
        act_metadata.triggered.connect(self.show_metadata_gui)

        self.act_folder = self.toolbar_control.addAction(
            "Save in {}".format(self.experiment.base_dir)
        )
        self.act_folder.triggered.connect(self.change_folder_gui)

        if self.experiment.database is not None:
            self.chk_db = QToolButton()
            self.chk_db.setText("Use DB")
            self.db_on_icon = QIcon(pkg_resources.resource_filename(__name__, "../icons/dbON.svg"),)
            self.db_off_icon = QIcon(pkg_resources.resource_filename(__name__,
                                                                    "../icons/dbOFF.svg"), )
            self.chk_db.setIcon(self.db_on_icon)
            self.chk_db.setCheckable(True)
            self.chk_db.setChecked(self.experiment.use_db)
            self.chk_db.clicked.connect(self.toggle_db)
            self.toggle_db()
            self.toolbar_control.addWidget(self.chk_db)

        if experiment.trigger is not None:
            self.chk_scope = QCheckBox("Wait for trigger signal")

        self.logger = QPlainTextEditLogger()
        self.experiment.logger.addHandler(self.logger)

        self.status_display = StatusMessageDisplay()
        self.statusBar().addWidget(self.status_display)

        self.metadata_win = None

    def change_folder_gui(self):
        folder = QFileDialog.getExistingDirectory(
            caption="Results folder", directory=self.experiment.base_dir
        )
        if folder is not None:
            self.experiment.base_dir = folder
            self.act_folder.setText("Save in {}".format(self.experiment.base_dir))

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

    def toggle_db(self):
        if self.chk_db.isChecked():
            self.chk_db.setIcon(self.db_on_icon)
            self.experiment.use_db = True
        else:
            self.chk_db.setIcon(self.db_off_icon)
            self.experiment.use_db = False

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
        self.plot_framerate.setMaximumHeight(120)

        self.status_display.addMessageQueue(self.experiment.camera.message_queue)

    def construct_ui(self):
        previous_widget = super().construct_ui()

        self.experiment.gui_timer.timeout.connect(self.plot_framerate.update)
        self.experiment.gui_timer.timeout.connect(self.status_display.refresh)

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

        super().construct_ui()
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        # TODO put in right place
        monitoring_widget = QWidget()
        monitoring_widget.setLayout(self.monitoring_layout)
        monitoring_dock = QDockWidget("Tracking", self)
        monitoring_dock.setWidget(monitoring_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, monitoring_dock)
        self.docks.append(monitoring_dock)


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

        if tail:
            self.tail_widget = TailStreamPlot(self.experiment.acc_tracking, [])

        # Tracking params button:
        self.button_tracking_params = QToolButton()
        self.button_tracking_params.setToolTip(
            "Tracking params"
        )
        self.button_tracking_params.setIcon(QIcon(pkg_resources.resource_filename(__name__, "../icons/edit_tracking.svg"),))
        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)

        self.camera_display.layout_control.addStretch(10)
        self.camera_display.layout_control.addWidget(self.button_tracking_params)

        self.track_params_wnd = None

        for fd in self.experiment.frame_dispatchers:
            self.status_display.addMessageQueue(fd.message_queue)

    def construct_ui(self):
        """ """
        previous_widget = super().construct_ui()
        self.experiment.gui_timer.timeout.connect(
            self.stream_plot.update

        )

        monitoring_widget = QWidget()
        monitoring_widget.setLayout(self.monitoring_layout)
        monitoring_dock = QDockWidget("Monitoring", self)
        monitoring_dock.setObjectName("dock_monitoring")
        monitoring_dock.setWidget(monitoring_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, monitoring_dock)
        self.docks.append(monitoring_dock)

        if self.tail:
            self.experiment.gui_timer.timeout.connect(
                self.tail_widget.update
            )
            tail_dock = QDockWidget("Tail curvature", self)
            tail_dock.setObjectName("dock_tail")
            tail_dock.setWidget(self.tail_widget)
            self.docks.append(tail_dock)
            self.addDockWidget(Qt.NoDockWidgetArea, tail_dock)
            tail_dock.setVisible(False)


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