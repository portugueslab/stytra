from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout,\
    QPushButton

import numpy as np
import pyqtgraph as pg

from stytra.gui.parameter_widgets import ParameterSpinBox
from PyQt5.QtWidgets import QVBoxLayout


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


# TODO: probably these widget parts should go elsewhere to leave here only
#       complete windows
class ProjectorViewer(pg.GraphicsLayoutWidget):
    """ Widget that displays the whole projector screen and allows to
    set the stimulus display window
    """
    def __init__(self, *args, display_size=(1280, 800), params_roi, **kwargs):
        super().__init__(*args, **kwargs)

        self.view_box = pg.ViewBox(invertY=True, lockAspect=1,
                                   enableMouse=False)
        self.addItem(self.view_box)

        # Create a ROI tool for selecting the area on the projector where the
        # stimulus will be displayed.

        # The ROI in Params is passed to log and restore the position:
        self.params_roi = params_roi
        self.roi_box = pg.ROI(maxBounds=QRectF(0, 0, display_size[0],
                                               display_size[1]),
                              size=params_roi['size'],
                              pos=params_roi['pos'])

        self.roi_box.addScaleHandle([0, 0], [1, 1])
        self.roi_box.addScaleHandle([1, 1], [0, 0])
        self.roi_box.sigRegionChangeFinished.connect(self.set_pos_from_roi)
        self.params_roi.sigTreeStateChanged.connect(self.set_pos_from_tree)

        self.view_box.addItem(self.roi_box)
        self.view_box.setRange(QRectF(0, 0, display_size[0], display_size[1]),
                               update=True, disableAutoRange=True)
        self.view_box.addItem(pg.ROI(pos=(1, 1), size=(display_size[0]-1,
                              display_size[1]-1), movable=False,
                                     pen=(80, 80, 80)))

        # Visualization of the calibration patterns:
        self.calibration_points = pg.ScatterPlotItem()
        self.calibration_frame = pg.PlotCurveItem(brush=(120, 10, 10),
                                                  pen=(200, 10, 10),
                                                  fill_level=1)
        self.view_box.addItem(self.calibration_points)
        self.view_box.addItem(self.calibration_frame)

    def set_pos_from_tree(self):
        """ Called when ROI position values are changed in the ParameterTree.
        Change the position of the displayed ROI:
        """
        self.roi_box.setPos(self.params_roi['pos'], finish=False)
        self.roi_box.setSize(self.params_roi['size'])

    def set_pos_from_roi(self):
        """ Called when ROI position values are changed in the displayed ROI.
        Change the position in the ParameterTree values.
        """

        # the treeChangeBlocker send a single signal at the end of all the
        # changes:
        with self.params_roi.treeChangeBlocker():
            self.params_roi.param('size').setValue(tuple(
                [int(p) for p in self.roi_box.size()]))
            self.params_roi.param('pos').setValue(tuple(
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
            pass  # TODO place transformed image


class ProjectorAndCalibrationWidget(QWidget):
    sig_calibrating = pyqtSignal()

    def __init__(self, experiment, **kwargs):
        """ Instantiate the widget that controls the display on the projector
        :param experiment: Experiment class with calibrator and display window.
        """
        super().__init__(**kwargs)
        self.experiment = experiment
        self.calibrator = experiment.calibrator
        self.container_layout = QVBoxLayout()
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        self.widget_proj_viewer = ProjectorViewer(params_roi=
                                                  experiment.window_display.params)

        self.container_layout.addWidget(self.widget_proj_viewer)

        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton('Show calibration')
        self.button_show_calib.clicked.connect(self.toggle_calibration)

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

