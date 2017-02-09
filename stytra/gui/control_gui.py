from PyQt5.QtCore import QRectF, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QLayout
import pyqtgraph as pg
import numpy as np


class ProjectorViewer(pg.GraphicsLayoutWidget):
    def __init__(self, *args, display_size=(1280, 800),ROI_desc=None,  **kwargs):
        super().__init__(*args, **kwargs)

        self.view_box = pg.ViewBox(invertY=True, lockAspect=1, enableMouse=False)
        self.addItem(self.view_box)

        self.roi_box = pg.ROI(maxBounds=QRectF(0, 0, display_size[0],
                                               display_size[1]), **ROI_desc)
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
        self.calibration_frame = pg.PlotCurveItem(brush=(120, 10, 10), pen=(200, 10, 10), fill_level=1)
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
            pass
            # TODO place transforemd image


class ProtocolControlWindow(QWidget):
    sig_calibrating = pyqtSignal()
    sig_closing = pyqtSignal()

    def __init__(self, app, protocol, display_window, *args):
        """ Class for controlling the stimuli
        """
        super().__init__(*args)
        self.app = app
        self.protocol = protocol
        self.display_window = display_window

        ROI_desc = self.display_window.display_params['window']

        # This part can be used for correctly display the  projectionViewer
        # once the experiment folder parameter is passed to the window.
        # Anyway, it would be better to take care of this from the DataCollector
        # set_to_last_value method.

        # import deepdish as dd
        # import os
        # experiment_folder = ''
        # list_metadata = [fn for fn in os.listdir(experiment_folder) if fn.endswith('metadata.h5')]
        # if len(list_metadata) > 0:
        #   last_metadata = dd.io.load(experiment_folder + list_metadata[-1])
        #   ROI_desc = dict(pos=last_metadata['stimulus']['window_pos'],
        #                   size=last_metadata['stimulus']['window_size'])

        self.widget_view = ProjectorViewer(ROI_desc=ROI_desc)

        self.button_update_display = QPushButton('Update display area')
        self.button_update_display.clicked.connect(self.refresh_ROI)

        self.layout_calibrate = QHBoxLayout()
        self.button_show_calib = QPushButton('Show calibration')
        self.button_show_calib.clicked.connect(self.toggle_calibration)
        self.button_calibrate = QPushButton('Calibrate')
        self.layout_calibrate.addWidget(self.button_show_calib)
        self.layout_calibrate.addWidget(self.button_calibrate)

        self.button_start = QPushButton('Start protocol')
        self.button_start.clicked.connect(self.protocol.start)

        self.button_end = QPushButton('End protocol')
        self.button_end.clicked.connect(self.protocol.end)

        self.button_metadata = QPushButton('Edit metadata')

        self.timer = None
        self.layout = QVBoxLayout()
        for widget in [
                       self.widget_view, self.button_update_display,
                       self.layout_calibrate, self.button_start,
                       self.button_end, self.button_metadata]:
            if isinstance(widget, QWidget):
                self.layout.addWidget(widget)
            if isinstance(widget, QLayout):
                self.layout.addLayout(widget)

        self.setLayout(self.layout)

    def reset_ROI(self):
        self.widget_view.roi_box.setPos(self.display_window.display_params['window']['pos'])
        self.widget_view.roi_box.setSize(self.display_window.display_params['window']['size'])

    def refresh_ROI(self):
        self.display_window.set_dims(self.widget_view.roi_box.pos(),
                                     self.widget_view.roi_box.size())

    def closeEvent(self, QCloseEvent):
        """ On closing the app, save where the window was

        :param QCloseEvent:
        :return: None
        """
        self.sig_closing.emit()
        self.deleteLater()
        self.app.quit()

    def toggle_calibration(self):
        dispw = self.display_window.widget_display
        dispw.calibrating = ~dispw.calibrating
        if dispw.calibrating:
            self.button_show_calib.setText('Hide calibration')
        else:
            self.button_show_calib.setText('Show calibration')
        dispw.update()
        self.sig_calibrating.emit()
