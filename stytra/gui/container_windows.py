from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout,\
    QPushButton, QComboBox

from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.protocol_control import ProtocolControlWidget
from stytra.gui.camera_display import CameraTailSelection, CameraViewWidget,\
    CameraEyesSelection

from PyQt5.QtWidgets import QMainWindow, QCheckBox, QVBoxLayout, QSplitter
from pyqtgraph.parametertree import ParameterTree
from stytra.gui.monitor_control import ProjectorAndCalibrationWidget


class DebugLabel(QLabel):
    def __init__(self, *args, debug_on=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('border-radius: 2px')
        self.set_debug(debug_on)
        self.setMinimumHeight(36)

    def set_debug(self, debug_on=False):
        if debug_on:
            self.setText('Debug mode is on, data will not be saved!')
            self.setStyleSheet('background-color: #dc322f;color:#fff')
        else:
            self.setText('Experiment ready, please ensure the metadata is correct')
            self.setStyleSheet('background-color: #002b36')


class TrackingSettingsGui(QWidget):
    def __init__(self):
        self.combo_method = QComboBox()
        self.combo_method.set_editable(False)


class SimpleExperimentWindow(QMainWindow):
    """ Window for controlling a simple experiment including only a monitor
    the relative controls and the buttons for metadata and protocol control.
    """
    def __init__(self, experiment, **kwargs):
        """
        :param experiment: Experiment class with metadata
        """
        super().__init__(**kwargs)
        self.experiment = experiment

        self.setWindowTitle('Stytra')

        self.label_debug = DebugLabel(debug_on=experiment.debug_mode)
        self.widget_projection = ProjectorAndCalibrationWidget(experiment)
        self.widget_control = ProtocolControlWidget(experiment)
        self.button_metadata = QPushButton('Edit metadata')

        if experiment.scope_triggered:
            self.chk_scope = QCheckBox('Wait for the scope')
        self.button_metadata.clicked.connect(
            self.show_metadata_gui)

        self.setCentralWidget(self.construct_ui())

        self.metadata_win = None

    def show_metadata_gui(self):
        self.metadata_win = QWidget()
        self.metadata_win.setLayout(QHBoxLayout())
        self.metadata_win.layout().addWidget(self.experiment.metadata.show_metadata_gui())
        self.metadata_win.layout().addWidget(self.experiment.fish_metadata.show_metadata_gui())
        self.metadata_win.show()

    def construct_ui(self):
        central_widget = QWidget()
        central_widget.setLayout(QVBoxLayout())
        central_widget.layout().addWidget(self.label_debug)
        central_widget.layout().addWidget(self.widget_projection)
        central_widget.layout().addWidget(self.widget_control)
        if self.experiment.scope_triggered:
            central_widget.layout().addWidget(self.chk_scope)
        central_widget.layout().addWidget(self.button_metadata)
        return central_widget

    def closeEvent(self, *args, **kwargs):
        self.experiment.wrap_up()


class CameraExperimentWindow(SimpleExperimentWindow):
    def __init__(self, *args, **kwargs):
        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.camera_display = CameraViewWidget(kwargs['experiment'])
        super().__init__(*args, **kwargs)

    def construct_ui(self):
        previous_widget = super().construct_ui()
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(previous_widget)
        return self.camera_splitter


class TailTrackingExperimentWindow(SimpleExperimentWindow):
    """ Window for controlling an experiment where the tail of an
    embedded fish is tracked.
    """
    def __init__(self,  *args, **kwargs):
        self.camera_display = CameraTailSelection(kwargs['experiment'])

        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)

        # Tracking params button:
        self.button_tracking_params = QPushButton('Tracking params')
        self.button_tracking_params.clicked.connect(
            self.open_tracking_params_tree)
        self.monitoring_layout.addWidget(self.button_tracking_params)

        self.track_params_wnd = None
        # self.tracking_layout.addWidget(self.camera_display)
        # self.tracking_layout.addWidget(self.button_tracking_params)

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        self.stream_plot.add_stream(self.experiment.data_acc,
                                    ['tail_sum'])
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(self.monitoring_widget)
        return self.camera_splitter

    def open_tracking_params_tree(self):
        self.track_params_wnd = ParameterTree()
        self.track_params_wnd.setParameters(self.experiment.tracking_method.params,
                                            showTop=False)
        self.track_params_wnd.setWindowTitle('Tracking data')
        self.track_params_wnd.show()


class EyeTrackingExperimentWindow(SimpleExperimentWindow):
    """ Window for controlling an experiment where the tail and the eyes
    of an embedded fish are tracked.
    """
    def __init__(self,  *args, **kwargs):
        self.camera_display = CameraEyesSelection(kwargs['experiment'])

        self.camera_splitter = QSplitter(Qt.Horizontal)
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        # Stream plot:
        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)

        # Tracking params button:
        self.button_tracking_params = QPushButton('Tracking params')
        self.button_tracking_params.clicked.connect(
            self.open_tracking_params_tree)
        self.monitoring_layout.addWidget(self.button_tracking_params)

        self.track_params_wnd = None
        # self.tracking_layout.addWidget(self.camera_display)
        # self.tracking_layout.addWidget(self.button_tracking_params)

        super().__init__(*args, **kwargs)

    def construct_ui(self):
        self.stream_plot.add_stream(self.experiment.data_acc,
                                    ['eye_1_th', 'eye_1_th'])
        self.experiment.gui_timer.timeout.connect(self.stream_plot.update)
        previous_widget = super().construct_ui()
        self.monitoring_layout.addWidget(previous_widget)
        self.monitoring_layout.setStretch(1, 1)
        self.monitoring_layout.setStretch(0, 1)
        self.camera_splitter.addWidget(self.camera_display)
        self.camera_splitter.addWidget(self.monitoring_widget)
        return self.camera_splitter

    def open_tracking_params_tree(self):
        self.track_params_wnd = ParameterTree()
        self.track_params_wnd.setParameters(self.experiment.tracking_method.params,
                                            showTop=False)
        self.track_params_wnd.setWindowTitle('Tracking data')
        self.track_params_wnd.show()


class VRExperimentWindow(SimpleExperimentWindow):
    def reconfigure_ui(self):
        self.main_layout = QSplitter()
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.positionPlot = StreamingPositionPlot(data_accumulator=
                                                  self.protocol.dynamic_log)
        self.monitoring_layout.addWidget(self.positionPlot)
        self.gui_refresh_timer.timeout.connect(self.positionPlot.update)

        self.stream_plot = MultiStreamPlot()

        self.monitoring_layout.addWidget(self.stream_plot)
        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)

        self.stream_plot.add_stream(self.experiment.data_acc_tailpoints,
                                    ['tail_sum', 'theta_01'])

        self.stream_plot.add_stream(self.experiment.position_estimator.log,
                                    ['v_ax',
                                         'v_lat',
                                         'v_ang',
                                         'middle_tail',
                                         'indexes_from_past_end'])

        self.main_layout.addWidget(self.monitoring_widget)
        self.main_layout.addWidget(self.controls_widget)
        self.setCentralWidget(self.main_layout)


class LightsheetGUI(SimpleExperimentWindow):
    def init_ui(self):
        self.chk_lightsheet = QCheckBox("Wait for lightsheet")
        self.chk_lightsheet.setChecked(False)
