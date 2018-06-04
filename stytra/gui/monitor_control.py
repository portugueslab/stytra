from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout,\
    QPushButton

import numpy as np
import pyqtgraph as pg

from stytra.gui.parameter_widgets import ParameterSpinBox
from stytra.calibration import CircleCalibrator, CrossCalibrator,\
    CalibrationException
from PyQt5.QtWidgets import QVBoxLayout


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

        self.calibration_points = pg.ScatterPlotItem(pen=None, brush=(255, 0, 0))
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
        points_proj = (points_cam @ np.array(calibrator.params["cam_to_proj"]).T)
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
        try:
            self.calibrator.find_transform_matrix(frame)
            self.widget_proj_viewer.display_calibration_pattern(self.calibrator,
                                                                frame.shape, frame)

        except CalibrationException:
            pass
