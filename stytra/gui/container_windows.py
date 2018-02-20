from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QHBoxLayout,\
    QPushButton, QComboBox


from stytra.calibration import CircleCalibrator
from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.protocol_control import ProtocolControlWidget
from stytra.gui.camera_display import CameraTailSelection, CameraViewCalib, CameraViewWidget

import numpy as np
import pyqtgraph as pg

from stytra.gui.parameter_widgets import ParameterSpinBox
from PyQt5.QtWidgets import QMainWindow, QCheckBox, QVBoxLayout, QSplitter
from pyqtgraph.parametertree import ParameterTree


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


class ProjectorViewer(pg.GraphicsLayoutWidget):
    """ Widget that displays the whole projector screen and allows to
    set the stimulus display window

    """
    def __init__(self, *args, display_size=(1280, 800), roi_params,  **kwargs):
        super().__init__(*args, **kwargs)

        self.roi_params = roi_params

        self.view_box = pg.ViewBox(invertY=True, lockAspect=1,
                                   enableMouse=False)
        self.addItem(self.view_box)

        self.roi_box = pg.ROI(maxBounds=QRectF(0, 0, display_size[0],
                                               display_size[1]),
                              size=roi_params['size'],
                              pos=roi_params['pos'])

        self.roi_box.addScaleHandle([0, 0], [1, 1])
        self.roi_box.addScaleHandle([1, 1], [0, 0])
        self.roi_box.sigRegionChangeFinished.connect(self.set_param_val)
        self.roi_params.sigTreeStateChanged.connect(self.set_roi)
        self.view_box.addItem(self.roi_box)
        self.view_box.setRange(QRectF(0, 0, display_size[0], display_size[1]),
                               update=True, disableAutoRange=True)
        self.view_box.addItem(pg.ROI(pos=(1, 1), size=(display_size[0]-1,
                              display_size[1]-1), movable=False,
                                     pen=(80, 80, 80)))

        self.calibration_points = pg.ScatterPlotItem()
        self.calibration_frame = pg.PlotCurveItem(brush=(120, 10, 10),
                                                  pen=(200, 10, 10),
                                                  fill_level=1)
        self.view_box.addItem(self.calibration_points)
        self.view_box.addItem(self.calibration_frame)

    def set_roi(self):
        self.roi_box.setPos(self.roi_params['pos'], finish=False)
        self.roi_box.setSize(self.roi_params['size'])

    def set_param_val(self):
        with self.roi_params.treeChangeBlocker():
            self.roi_params.param('size').setValue(tuple(
                [int(p) for p in self.roi_box.size()]))
            self.roi_params.param('pos').setValue(tuple(
                [int(p) for p in self.roi_box.pos()]))

    def display_calibration_pattern(self, calibrator,
                                    camera_resolution=(480, 640),
                                    image=None):
        cw = camera_resolution[0]
        ch = camera_resolution[1]
        points_cam = np.array([[0, 0], [0, cw],
                              [ch, cw], [ch, 0], [0, 0]])

        points_cam = np.pad(points_cam, ((0, 0), (0, 1)),
                            mode='constant', constant_values=1)
        points_calib = np.pad(calibrator.points, ((0, 0), (0, 1)),
                              mode='constant', constant_values=1)
        points_proj = (points_cam @ calibrator.cam_to_proj.T)
        x0, y0 = self.roi_box.pos()
        self.calibration_frame.setData(x=points_proj[:, 0]+x0,
                                       y=points_proj[:, 1]+y0)
        self.calibration_points.setData(x=points_calib[:, 0]+x0,
                                        y=points_calib[:, 1]+y0)
        if image is not None:
            pass # TODO place transformed image


class ProjectorAndCalibrationWidget(QWidget):
    sig_calibrating = pyqtSignal()

    def __init__(self, experiment, **kwargs):
        """ Instantiate the widget that controls the display on the projector

        :param experiment: Experiment class with calibrator and display window
        """
        super().__init__(**kwargs)
        self.experiment = experiment
        self.calibrator = experiment.calibrator
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        self.widget_proj_viewer = ProjectorViewer(roi_params=
                                                  experiment.window_display.params)

        self.container_layout.addWidget(self.widget_proj_viewer)

        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton('Show calibration')
        self.button_show_calib.clicked.connect(self.toggle_calibration)

        if isinstance(experiment.calibrator, CircleCalibrator):
            self.button_calibrate = QPushButton('Calibrate')
            self.button_calibrate.clicked.connect(self.calibrate)
            self.layout_calibrate.addWidget(self.button_calibrate)

        self.label_calibrate = QLabel('size of calib. pattern in mm')
        self.layout_calibrate.addWidget(self.button_show_calib)
        self.layout_calibrate.addWidget(self.label_calibrate)
        self.calibrator_len_spin = ParameterSpinBox(
            parameter=self.calibrator.params.param('length_mm'))

        self.layout_calibrate.addWidget(self.calibrator_len_spin)

        self.container_layout.addLayout(self.layout_calibrate)
        self.setLayout(self.container_layout)

    def toggle_calibration(self):
        self.calibrator.toggle()
        if self.calibrator.enabled:
            self.button_show_calib.setText('Hide calibration')
        else:
            self.button_show_calib.setText('Show calibration')
        self.sig_calibrating.emit()
        self.experiment.window_display.widget_display.update()

    def calibrate(self):
        _, frame = self.experiment.frame_dispatcher.gui_queue.get()
        self.calibrator.find_transform_matrix(frame)
        self.widget_proj_viewer.display_calibration_pattern(self.calibrator, frame.shape, frame)


class TrackingSettingsGui(QWidget):
    def __init__(self):
        self.combo_method = QComboBox()
        self.combo_method.set_editable(False)


class SimpleExperimentWindow(QMainWindow):
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


# TAIL TRACKING LAYOUT
#     self.main_layout = QSplitter()
#         self.monitoring_widget = QWidget()
#         self.monitoring_layout = QVBoxLayout()
#         self.monitoring_widget.setLayout(self.monitoring_layout)
#
#         self.stream_plot = MultiStreamPlot()
#
#         self.monitoring_layout.addWidget(self.stream_plot)
#         self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
#
#         self.stream_plot.add_stream(self.data_acc_tailpoints,
#                                     ['tail_sum', 'theta_01'])
#
#         self.main_layout.addWidget(self.monitoring_widget)
#         self.main_layout.addWidget(self.widget_control)
#         self.setCentralWidget(self.main_layout)
#
#         self.positionPlot = None


class TailTrackingExperimentWindow(SimpleExperimentWindow):
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
        self.stream_plot.add_stream(self.experiment.data_acc_tailpoints,
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
