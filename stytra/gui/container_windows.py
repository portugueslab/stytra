from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QHBoxLayout,\
    QPushButton, QSplitter, QVBoxLayout

from stytra.gui.plots import StreamingPositionPlot, MultiStreamPlot
from stytra.gui.camera_display import CameraTailSelection, CameraViewCalib

import numpy as np
import pyqtgraph as pg

from stytra.gui.parameter_widgets import ParameterSpinBox
from PyQt5.QtWidgets import QMainWindow, QCheckBox, QVBoxLayout, QSplitter

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
        self.view_box.addItem(self.roi_box)
        self.view_box.setRange(QRectF(0, 0, display_size[0], display_size[1]),
                               update=True, disableAutoRange=True)
        self.view_box.addItem(pg.ROI(pos=(1, 1), size=(display_size[0]-1,
                              display_size[1]-1), movable=False,
                                     pen=(80, 80, 80)),
                              )

        self.calibration_points = pg.ScatterPlotItem()
        self.calibration_frame = pg.PlotCurveItem(brush=(120, 10, 10),
                                                  pen=(200, 10, 10),
                                                  fill_level=1)
        self.view_box.addItem(self.calibration_points)
        self.view_box.addItem(self.calibration_frame)

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

    def __init__(self, *args, calibrator, **kwargs):
        """ Instantiate the widget that controls the display on the projector

        :param args:
        :param calibrator:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.calibrator = calibrator
        self.container_layout = QVBoxLayout()

        self.widget_proj_viewer = ProjectorViewer()

        self.container_layout.addWidget()

        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton('Show calibration')
        self.label_calibrate = QLabel('size of calib. pattern in mm')
        self.layout_calibrate.addWidget(self.button_show_calib)
        self.layout_calibrate.addWidget(self.label_calibrate)
        self.calibrator_len_spin = ParameterSpinBox(
            parameter=self.calibrator.params.param('length_mm'))

        self.layout_calibrate.addWidget(self.calibrator_len_spin)

        self.button_show_calib.clicked.connect(self.toggle_calibration)


        # TODO move to a more reasonable place
        self.widget_view.roi_box.sigRegionChangeFinished.connect(
            self.refresh_ROI)

    def reset_ROI(self):
        self.widget_view.roi_box.setPos(self.display_window.params['pos'], finish=False)
        self.widget_view.roi_box.setSize(self.display_window.params['size'])
        self.refresh_ROI()

    def refresh_ROI(self):
        if self.display_window:
            self.display_window.set_dims(tuple([int(p) for p in
                                                self.widget_view.roi_box.pos()]),
                                         tuple([int(p) for p in
                                                self.widget_view.roi_box.size()]))

    def toggle_calibration(self):
        self.calibrator.toggle()
        print(self.calibrator)
        if self.calibrator.enabled:
            self.button_show_calib.setText('Hide calibration')
        else:
            self.button_show_calib.setText('Show calibration')
        self.display_window.widget_display.update()
        self.experiment.sig_calibrating.emit()


class SimpleExperimentWindow(QMainWindow):
    def __init__(self, *args, experiment, **kwargs):
        super().__init__(*args, **kwargs)
        self.experiment = experiment

        self.label_debug = DebugLabel(debug_on=experiment.debug_mode)

        self.button_metadata = QPushButton('Edit metadata')
        self.button_metadata.clicked.connect(
            self.experiment.metadata.show_metadata_gui)

        self.widget_projection = ProjectorAndCalibrationWidget(experiment.calibrator)



class VRExperimentWindow(SimpleExperimentWindow):
    def reconfigure_ui(self):
        self.main_layout = QSplitter()
        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.positionPlot = StreamingPositionPlot(data_accumulator=self.protocol.dynamic_log)
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