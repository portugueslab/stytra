from PyQt5.QtCore import QTimer, Qt, QRectF, QObject, QPoint, QPointF
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
import pyqtgraph as pg
from queue import Empty
import numpy as np
from paramqt import ParameterGui
from multiprocessing import Queue
from skimage.io import imsave


class CameraViewWidget(QWidget):
    def __init__(self, experiment):
        """
        A widget to show the camera and display the controls
        :param experiment: experiment to which this belongs
        :param camera: the camera object
        """

        super().__init__()

        self.camera_queue = Queue()
        self.camera_display_widget = pg.GraphicsLayoutWidget()

        self.display_area = pg.ViewBox(lockAspect=1, invertY=False)
        self.camera_display_widget.addItem(self.display_area)

        self.display_area.setRange(QRectF(0, 0, 640, 640), update=True,
                                   disableAutoRange=True)
        self.image_item = pg.ImageItem()
        self.image_item.setImage(np.zeros((640, 480), dtype=np.uint8))
        self.display_area.addItem(self.image_item)

        self.experiment = experiment
        self.camera = experiment.camera

        self.frame_queue = self.camera.frame_queue
        self.control_queue = self.camera.control_queue
        self.camera_rotation = self.camera.rotation
        experiment.gui_timer.timeout.connect(self.update_image)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.camera_display_widget)
        if self.control_queue is not None:
            try:
                self.camera_parameters = self.camera.camera_parameters
                self.control_widget = ParameterGui(self.camera_parameters)
                self.layout.addWidget(self.control_widget)
                for control in self.control_widget.parameter_controls:
                    control.control_widget.valueChanged.connect(self.update_controls)
                self.control_queue.put(self.camera_parameters.get_param_dict())
            except AttributeError:
                pass

        self.captureButton = QPushButton('Capture frame')
        self.captureButton.clicked.connect(self.save_image)
        self.layout.addWidget(self.captureButton)
        self.current_image = None

        self.setLayout(self.layout)

    def update_controls(self):
        self.control_widget.save_meta()
        self.control_queue.put(self.camera_parameters.get_param_dict())

    def update_image(self):
        im_in = None
        first = True
        while True:
            try:
                if first:
                    time, self.current_image = self.camera.frame_queue.get(
                        timeout=0.001)
                    first = False
                else:
                    _, _ = self.camera_queue.get(timeout=0.001)

                if self.camera_rotation >= 1:
                    self.current_image = np.rot90(self.current_image,
                                                  k=self.camera_rotation)

            except Empty:
                break
        if self.current_image is not None:
            self.image_item.setImage(self.current_image)

    def save_image(self):
        """ Save a frame to the current directory.
        """
        # TODO getting errors here
        # TODO name image with time
        imsave(self.experiment.directory + '/img.png', self.image_item)


class CameraTailSelection(CameraViewWidget):
    def __init__(self, experiment, **kwargs):
                 # tail_start_points_queue, tail_position_data,
                 # roi_dict=None, tracking_params=None,
        """ Widget for select tail points and monitoring tracking in embedded animal.
        :param tail_start_points_queue: queue where to dispatch tail points
        :param tail_position_data: DataAccumulator object for tail pos data.
        :param roi_dict: dictionary for setting default tail position
        """
        self.tail_position_data = Queue()  # tail_position_data
        super().__init__(experiment)
        self.tail_start_points_queue = Queue()  # tail_start_points_queue
        print('hic et nunc')

        # self.label = pg.TextItem('Select tail of the fish:')

        # if not roi_dict:  # use input dictionary
        # self.roi_dict = {'tail_start': self.experiment.tracking_method.params['tail_start'],
        #                  'tail_length': self.experiment.tracking_method.params['tail_length']}
        # self.roi_dict = roi_dict
        self.track_params = self.experiment.tracking_method.params
        # Draw ROI for tail selection:
        # print('start: {}'.format(self.track_params['tail_start']))
        # print('size: {}'.format(self.track_params['tail_length']))
        self.roi_tail = pg.LineSegmentROI((self.track_params['tail_start'],
                                          (self.track_params['tail_start'][0] +
                                           self.track_params['tail_length'][0],
                                           self.track_params['tail_start'][1] +
                                           self.track_params['tail_length'][1]
                                           )), pen=dict(color=(230, 40, 5),
                                                        width=3))

        self.tail_curve = pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                    width=3))
        self.display_area.addItem(self.tail_curve)
        self.display_area.addItem(self.roi_tail)

        # self.tail_start_points_queue.put(self.get_tracking_params())
        self.roi_tail.sigRegionChangeFinished.connect(self.set_param_val)
        self.track_params.sigTreeStateChanged.connect(self.set_roi)

    def set_roi(self):
        p1, p2 = self.roi_tail.getHandles()
        p1.setPos(QPointF(*self.track_params['tail_start']))
        p2.setPos(QPointF(self.track_params['tail_start'][0] + \
                           self.track_params['tail_length'][0],
                           self.track_params['tail_start'][1] + \
                           self.track_params['tail_length'][1]))

    def set_param_val(self):
        p1, p2 = self.roi_tail.getHandles()
        with self.track_params.treeChangeBlocker():
            self.track_params.param('tail_start').setValue((
                p1.x(), p1.y()))
            self.track_params.param('tail_length').setValue((
                p2.x() - p1.x(), p2.y() - p1.y()))

    def update_image(self):
        super().update_image()
        if len(self.experiment.data_acc_tailpoints.stored_data) > 1:
            angles = self.experiment.data_acc_tailpoints.stored_data[-1][2:]
            start_x = self.track_params['tail_start'][1]
            start_y = self.track_params['tail_start'][0]
            tail_len_x = self.track_params['tail_length'][1]
            tail_len_y = self.track_params['tail_length'][0]
            tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)

            # Get segment length:
            tail_segment_length = tail_length / (len(angles) - 1)
            points = [np.array([start_x, start_y])]
            for angle in angles:
                points.append(points[-1] + tail_segment_length * np.array(
                    [np.sin(angle), np.cos(angle)]))
            points = np.array(points)
            self.tail_curve.setData(x=points[:, 1], y=points[:, 0])


class CameraViewCalib(CameraViewWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.points_calib = pg.ScatterPlotItem()
        self.display_area.addItem(self.points_calib)

    def show_calibration(self, calibrator):
        if calibrator.proj_to_cam is not None:
            camera_points = np.pad(calibrator.points, ((0, 0), (0, 1)),
                                   mode='constant', constant_values=1) @ calibrator.proj_to_cam.T

            points_dicts = []
            for point in camera_points:
                xn, yn = point[::-1]
                points_dicts.append(dict(x=xn, y=yn, size=8,
                                         brush=(210, 10, 10)))

            self.points_calib.setData(points_dicts)

