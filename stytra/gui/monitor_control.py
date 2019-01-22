from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QPushButton

import numpy as np
import pyqtgraph as pg

from stytra.calibration import CircleCalibrator, CrossCalibrator, CalibrationException
from PyQt5.QtWidgets import QVBoxLayout
from lightparam.gui import ControlSpin

import cv2


class ProjectorViewer(pg.GraphicsLayoutWidget):
    """Widget that displays the whole projector screen and allows
     configuring the stimulus display window

    Parameters
    ----------

    Returns
    -------

    """

    sig_dim_changed = pyqtSignal(tuple)

    def __init__(self, *args, display_size=(1280, 800), display, **kwargs):
        super().__init__(*args, **kwargs)

        self.display = display

        self.view_box = pg.ViewBox(invertY=True, lockAspect=1, enableMouse=False)
        self.addItem(self.view_box)

        self.roi_box = pg.ROI(
            maxBounds=QRectF(0, 0, display_size[0], display_size[1]),
            size=display.size,
            pos=display.pos,
        )

        self.roi_box.addScaleHandle([0, 0], [1, 1])
        self.roi_box.addScaleHandle([1, 1], [0, 0])
        self.roi_box.sigRegionChanged.connect(self.set_param_val)
        self.display.sig_param_changed.connect(self.set_roi)
        self.view_box.addItem(self.roi_box)
        self.view_box.setRange(
            QRectF(0, 0, display_size[0], display_size[1]),
            update=True,
            disableAutoRange=True,
        )
        self.view_box.addItem(
            pg.ROI(
                pos=(1, 1),
                size=(display_size[0] - 1, display_size[1] - 1),
                movable=False,
                pen=(80, 80, 80),
            )
        )

        self.calibration_points = pg.ScatterPlotItem(pen=(255, 0, 0), brush=None)
        self.calibration_frame = pg.PlotCurveItem(
            brush=(120, 10, 10), pen=(200, 10, 10), fill_level=1
        )

        self.camera_image = pg.ImageItem()

        self.view_box.addItem(self.calibration_frame)
        self.view_box.addItem(self.camera_image)
        self.view_box.addItem(self.calibration_points)

        self.setting_param_val = False

        self.set_param_val()

    def set_roi(self):
        """ """
        if not self.setting_param_val:
            self.roi_box.setPos(self.display.pos)
            self.roi_box.setSize(self.display.size)

    def set_param_val(self):
        """ """
        self.setting_param_val = True
        size = tuple([int(p) for p in self.roi_box.size()])
        self.display.size = size
        self.sig_dim_changed.emit(size)

        self.display.pos = tuple([int(p) for p in self.roi_box.pos()])
        self.setting_param_val = False

    def display_calibration_pattern(
        self, calibrator, camera_resolution=(480, 640), image=None
    ):
        """

        Parameters
        ----------
        calibrator :
            
        camera_resolution :
             (Default value = (480)
        640) :
            
        image :
             (Default value = None)

        Returns
        -------

        """
        cw = camera_resolution[0]
        ch = camera_resolution[1]
        points_cam = np.array([[0, 0], [0, cw], [ch, cw], [ch, 0], [0, 0]])
        x0, y0 = self.roi_box.pos()

        try:
            points_calib = np.pad(
                calibrator.points, ((0, 0), (0, 1)), mode="constant", constant_values=1
            )
            self.calibration_points.setData(
                x=points_calib[:, 0] + x0, y=points_calib[:, 1] + y0
            )
        except ValueError:
            pass

        try:
            if calibrator.cam_to_proj is not None:
                points_cam = np.pad(
                    points_cam, ((0, 0), (0, 1)), mode="constant", constant_values=1
                )
                points_proj = points_cam @ np.array(calibrator.cam_to_proj).T

                self.calibration_frame.setData(
                    x=points_proj[:, 0] + x0, y=points_proj[:, 1] + y0
                )

            if image is not None and calibrator.cam_to_proj is not None:
                tr_im = cv2.warpAffine(
                    image,
                    np.array(calibrator.cam_to_proj).astype(np.float64),
                    dsize=tuple([int(p) for p in self.roi_box.size()]),
                )
                self.camera_image.setImage(tr_im)
                self.camera_image.setRect(
                    QRectF(
                        self.roi_box.pos().x(),
                        self.roi_box.pos().y(),
                        self.roi_box.size().x(),
                        self.roi_box.size().y(),
                    )
                )

        except ValueError:
            pass


class ProjectorAndCalibrationWidget(QWidget):
    """ """

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

        self.widget_proj_viewer = ProjectorViewer(display=experiment.window_display)
        self.container_layout.addWidget(self.widget_proj_viewer)

        self.widget_proj_viewer.sig_dim_changed.connect(self.update_size)

        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton("Show calibration")
        self.button_show_calib.clicked.connect(self.toggle_calibration)

        if isinstance(experiment.calibrator, CircleCalibrator):
            self.button_calibrate = QPushButton("Calibrate")
            self.button_calibrate.clicked.connect(self.calibrate)
            self.layout_calibrate.addWidget(self.button_calibrate)

        self.label_calibrate = QLabel(self.calibrator.length_to_measure)
        self.label_calibrate.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.layout_calibrate.addWidget(self.button_show_calib)
        self.layout_calibrate.addWidget(self.label_calibrate)

        self.calibrator_len_spin = ControlSpin(self.calibrator, "length_mm")

        self.layout_calibrate.addWidget(self.calibrator_len_spin)

        self.layout_calibrate.setContentsMargins(12, 0, 12, 12)
        self.container_layout.addLayout(self.layout_calibrate)
        self.setLayout(self.container_layout)

    def update_size(self, size):
        self.calibrator.set_pixel_scale(size[0], size[1])
        self.calibrator_len_spin.update_display()

    def toggle_calibration(self):
        """ """
        if isinstance(self.calibrator, CircleCalibrator):
            _, frame = self.experiment.frame_dispatcher.gui_queue.get()
            self.widget_proj_viewer.display_calibration_pattern(
                self.calibrator, frame.shape, frame
            )
        self.calibrator.toggle()
        if self.calibrator.enabled:
            self.button_show_calib.setText("Hide calibration")
        else:
            self.button_show_calib.setText("Show calibration")
        self.sig_calibrating.emit()
        self.experiment.window_display.widget_display.update()

    def calibrate(self):
        """ """
        _, frame = self.experiment.frame_dispatcher.gui_queue.get()
        try:
            self.calibrator.find_transform_matrix(frame)
            self.widget_proj_viewer.display_calibration_pattern(
                self.calibrator, frame.shape, frame
            )

        except CalibrationException:
            pass
