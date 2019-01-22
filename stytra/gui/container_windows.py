import logging
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPlainTextEdit,
    QMainWindow,
    QCheckBox,
    QVBoxLayout,
    QDockWidget,
    QFileDialog,
)

from stytra.gui.monitor_control import ProjectorAndCalibrationWidget
from stytra.gui.multiscope import MultiStreamPlot, FrameratePlot
from stytra.gui.protocol_control import ProtocolControlToolbar
from stytra.gui.camera_display import (
    CameraViewWidget
)
from stytra.gui.buttons import IconButton, ToggleIconButton
from stytra.gui.status_display import StatusMessageDisplay
from stytra.gui.framerate_viewer import MultiFrameratesWidget

from lightparam.gui import ParameterGui, pretty_name, ControlCombo, ControlButton


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


class ExperimentWindow(QMainWindow):
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

        self.setWindowTitle(
            "Stytra | " + pretty_name(type(experiment.protocol).name))

        self.docks = dict()

        # self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        # if not self.experiment.offline:
        #     self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        self.toolbar_control = ProtocolControlToolbar(
            experiment.protocol_runner, self)
        self.toolbar_control.setObjectName("toolbar")

        # Connect signals from the protocol_control:
        self.toolbar_control.sig_start_protocol.connect(
            experiment.start_protocol)
        self.toolbar_control.sig_stop_protocol.connect(experiment.end_protocol)

        self.btn_metadata = IconButton(
            icon_name="edit_fish", action_name="Edit metadata"
        )
        self.btn_metadata.clicked.connect(self.show_metadata_gui)
        self.toolbar_control.addWidget(self.btn_metadata)

        self.act_folder = self.toolbar_control.addAction(
            "Save in {}".format(self.experiment.base_dir)
        )
        self.act_folder.triggered.connect(self.change_folder_gui)

        if self.experiment.database is not None:
            self.chk_db = ToggleIconButton(
                action_on="Use DB",
                icon_on="dbON",
                icon_off="dbOFF",
                on=self.experiment.use_db,
            )
            self.chk_db.toggled.connect(self.toggle_db)
            self.toolbar_control.addWidget(self.chk_db)

        if experiment.trigger is not None:
            self.chk_scope = QCheckBox("Wait for trigger signal")

        self.logger = QPlainTextEditLogger()
        self.experiment.logger.addHandler(self.logger)

        self.status_display = StatusMessageDisplay()
        self.statusBar().addWidget(self.status_display)

        self.plot_framerate = MultiFrameratesWidget()
        self.plot_framerate.add_framerate(
            self.experiment.protocol_runner.framerate_acc)

        self.metadata_win = None

    def change_folder_gui(self):
        folder = QFileDialog.getExistingDirectory(
            caption="Results folder", directory=self.experiment.base_dir
        )
        if folder is not None:
            self.experiment.base_dir = folder
            self.act_folder.setText(
                "Save in {}".format(self.experiment.base_dir))

    def show_metadata_gui(self):
        """ """
        self.metadata_win = QWidget()
        self.metadata_win.setLayout(QHBoxLayout())
        self.metadata_win.layout().addWidget(
            ParameterGui(self.experiment.metadata))
        self.metadata_win.layout().addWidget(
            ParameterGui(self.experiment.metadata_animal)
        )
        self.metadata_win.show()

    def add_dock(self, item: QDockWidget):
        self.docks[item.objectName()] = item

    def construct_ui(self):
        """ """
        self.addToolBar(Qt.TopToolBarArea, self.toolbar_control)

        log_dock = QDockWidget("Log", self)
        log_dock.setObjectName("dock_log")
        log_dock.setWidget(self.logger.widget)
        self.add_dock(log_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, log_dock)

        dockFramerate = QDockWidget("Frame rates", self)
        dockFramerate.setWidget(self.plot_framerate)
        dockFramerate.setObjectName("dock_framerates")
        self.addDockWidget(Qt.RightDockWidgetArea, dockFramerate)
        self.add_dock(dockFramerate)

        if self.experiment.trigger is not None:
            self.toolbar_control.addWidget(self.chk_scope)

        self.experiment.gui_timer.timeout.connect(
                self.plot_framerate.update)

        self.toolbar_control.setObjectName("toolbar_control")
        self.setCentralWidget(None)

    def write_log(self, msg):
        self.log_widget.textCursor().appendPlainText(msg)

    def toggle_db(self, tg):
        if self.chk_db.isChecked():
            self.experiment.use_db = True
        else:
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


class VisualExperimentWindow(ExperimentWindow):
    """Window for controlling a simple experiment including only a monitor
    the relative controls and the buttons for data_log and protocol control.

    Parameters
    ----------
    experiment : `Experiment <stytra.experiments.Experiment>` object
        experiment for which the window is built.

    Returns
    -------

    """

    def __init__(self, *args, **kwargs):
        """ """
        super().__init__(*args, **kwargs)
        if not self.experiment.offline:
            self.widget_projection = ProjectorAndCalibrationWidget(self.experiment)

    def construct_ui(self):
        """ """
        super().construct_ui()

        if not self.experiment.offline:
            proj_dock = QDockWidget("Projector configuration", self)
            proj_dock.setWidget(self.widget_projection)
            proj_dock.setObjectName("dock_projector")
            self.add_dock(proj_dock)
            self.addDockWidget(Qt.RightDockWidgetArea, proj_dock)


class CameraExperimentWindow(VisualExperimentWindow):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.camera_display = None
        if hasattr(self.experiment, "pipeline"):
            self.camera_display = self.experiment.pipeline.display_overlay(
                experiment=self.experiment)
        else:
            self.camera_display = CameraViewWidget(experiment=kwargs["experiment"])

        self.plot_framerate.setMaximumHeight(120)

        self.status_display.addMessageQueue(self.experiment.camera.message_queue)

    def construct_ui(self):
        super().construct_ui()

        self.experiment.gui_timer.timeout.connect(self.status_display.refresh)

        dockCamera = QDockWidget("Camera", self)
        dockCamera.setWidget(self.camera_display)
        dockCamera.setObjectName("dock_camera")

        self.plot_framerate.add_framerate(self.experiment.acc_camera_framerate)

        self.addDockWidget(Qt.LeftDockWidgetArea, dockCamera)

        # moving the framerate dock
        self.removeDockWidget(self.docks["dock_framerates"])
        self.addDockWidget(Qt.LeftDockWidgetArea, self.docks["dock_framerates"])
        self.docks["dock_framerates"].setVisible(True)

        self.add_dock(dockCamera)


class DynamicStimExperimentWindow(VisualExperimentWindow):
    """Window for plotting a dynamically varying stimulus.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        self.stream_plot = MultiStreamPlot(experiment=self.experiment)
        self.monitoring_layout.addWidget(self.stream_plot)

    def construct_ui(self):
        """ """

        super().construct_ui()
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        # TODO put in right place
        monitoring_widget = QWidget()
        monitoring_widget.setLayout(self.monitoring_layout)
        monitoring_dock = QDockWidget("Tracking", self)
        monitoring_dock.setWidget(monitoring_widget)
        monitoring_dock.setObjectName("monitoring_dock")
        self.addDockWidget(Qt.RightDockWidgetArea, monitoring_dock)
        self.add_dock(monitoring_dock)


class TrackingExperimentWindow(CameraExperimentWindow):
    """Window for controlling an experiment where the tail of an
    embedded fish is tracked.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self, tracking=True, *args, **kwargs
    ):
        super().__init__(*args,  **kwargs)
        # TODO refactor movement detection
        self.tracking = tracking

        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.stream_plot = MultiStreamPlot(experiment=self.experiment)

        self.monitoring_layout.addWidget(self.stream_plot)

        self.extra_widget = (self.experiment.pipeline.extra_widget(
            self.experiment.acc_tracking)
                             if self.experiment.pipeline.extra_widget is not None
                             else None)

        # Display dropdown
        self.drop_display = ControlCombo(
            self.experiment.pipeline.all_params["diagnostics"],
        "image")

        if hasattr(self.camera_display, "set_pos_from_tree"):
            self.drop_display.control.currentTextChanged.connect(
                self.camera_display.set_pos_from_tree)

        # Tracking params button:
        self.button_tracking_params = IconButton(
            icon_name="edit_tracking", action_name="Change tracking parameters"
        )
        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)

        self.camera_display.layout_control.addStretch(10)
        self.camera_display.layout_control.addWidget(self.drop_display)
        self.camera_display.layout_control.addWidget(self.button_tracking_params)

        self.track_params_wnd = None

        self.status_display.addMessageQueue(self.experiment.frame_dispatcher.message_queue)

    def construct_ui(self):
        """ """
        previous_widget = super().construct_ui()
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)

        monitoring_widget = QWidget()
        monitoring_widget.setLayout(self.monitoring_layout)
        monitoring_dock = QDockWidget("Monitoring", self)
        monitoring_dock.setObjectName("dock_monitoring")
        monitoring_dock.setWidget(monitoring_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, monitoring_dock)
        self.add_dock(monitoring_dock)

        self.plot_framerate.add_framerate(self.experiment.acc_tracking_framerate)

        if self.extra_widget:
            self.experiment.gui_timer.timeout.connect(self.extra_widget.update)

            dock_extra = QDockWidget(self.extra_widget.title, self)
            dock_extra.setObjectName("dock_extra")
            dock_extra.setWidget(self.extra_widget)
            self.add_dock(dock_extra)
            self.addDockWidget(Qt.RightDockWidgetArea, dock_extra)
            dock_extra.setVisible(False)

        return previous_widget

    def open_tracking_params_tree(self):
        """ """
        self.track_params_wnd = QWidget()
        self.track_params_wnd.setLayout(QVBoxLayout())
        if hasattr(self.experiment, "pipeline"):
            for paramsname, paramspar in self.experiment.pipeline.all_params.items():
                if paramsname == "diagnostics" or paramsname == "reset" or \
                   len(paramspar.params.items()) == 0:
                    continue
                self.track_params_wnd.layout().addWidget(QLabel(paramsname.replace("/","→")))
                self.track_params_wnd.layout().addWidget(
                    ParameterGui(paramspar)
                )

        self.track_params_wnd.layout().addWidget(ControlButton(
            self.experiment.pipeline.all_params["reset"],
        "reset"))

        self.track_params_wnd.setWindowTitle("Tracking parameters")

        self.track_params_wnd.show()
