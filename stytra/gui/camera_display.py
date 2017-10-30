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
        # self.tracking_params = tracking_params

        # self.label = pg.TextItem('Select tail of the fish:')

        # if not roi_dict:  # use input dictionary
        # self.roi_dict = {'tail_start': self.experiment.tracking_method.params['tail_start'],
        #                  'tail_length': self.experiment.tracking_method.params['tail_length']}
        # self.roi_dict = roi_dict
        self.track_params = self.experiment.tracking_method.params
        # Draw ROI for tail selection:
        print('start: {}'.format(self.track_params['tail_start']))
        print('size: {}'.format(self.track_params['tail_length']))
        self.roi_tail = pg.LineSegmentROI(self.track_params['tail_start'],
                                          (self.track_params['tail_start'][0] +
                                           self.track_params['tail_length'][0],
                                           self.track_params['tail_start'][1] +
                                           self.track_params['tail_length'][1]),
                                          pen=dict(color=(230, 40, 5),
                                                   width=3))
        self.roi_tail.setPos(self.track_params['tail_start'])
        self.roi_tail.setSize(self.track_params['tail_length'])
        p1, p2 = self.roi_tail.getHandles()
        #self.set_roi()
        print('p1: {}, {}'.format(p1.x(), p1.y()))
        print('p2: {}, {}'.format(p2.x(), p2.y()))
                 #pen = None)
        # self.roi_tail = pg.LineSegmentROI(((self.roi_dict['start_y'],
        #                                     sel.roi_dict['start_x']),
        #                                    (sel.roi_dict['start_y'] + \
        #                                     sel.roi_dict['tail_length_y'],
        #                                     sel.roi_dict['start_x'] + \
        #                                     sel.roi_dict['tail_length_x'])),
        #                                   pen=None)

        self.tail_curve = pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                    width=3))
        self.display_area.addItem(self.tail_curve)
        self.display_area.addItem(self.roi_tail)

        # self.get_tracking_params()
        # self.tail_start_points_queue.put(self.get_tracking_params())
        self.roi_tail.sigRegionChangeFinished.connect(self.set_param_val)
        self.track_params.sigTreeStateChanged.connect(self.set_roi)

    def set_roi(self):
        pass
        # p1, p2 = self.roi_tail.getHandles()
        #print('p1: {}, {}'.format(p1.x(), p1.y()))
        #print('p2: {}, {}'.format(p2.x(), p2.y()))
        # p1.setPos(QPointF(*self.track_params['tail_start']))
        # p2.setPos(QPointF(self.track_params['tail_start'][0] + \
        #                   self.track_params['tail_length'][0],
        #                   self.track_params['tail_start'][1] + \
        #                   self.track_params['tail_length'][1]))
        # self.roi_box.setPos(self.roi_params['pos'], finish=False)
        # self.roi_box.setSize(self.roi_params['size'])
        # self.roi_tail.setPos()

    def set_param_val(self):
        p1, p2 = self.roi_tail.getHandles()
        with self.track_params.treeChangeBlocker():
            self.track_params.param('tail_start').setValue((
                p1.y(), p1.x()))
            self.track_params.param('tail_length').setValue((
                p1.y() - p2.y(), p1.x() - p2.x()))

    # def reset_ROI(self):
    #     def set_roi(self):
    #         self.roi_box.setPos(self.roi_params['pos'], finish=False)
    #         self.roi_box.setSize(self.roi_params['size'])
    #     # TODO figure out how to load handles
    #     # pass
    #     # self.roi_tail.setPoints(((self.roi_dict['start_y'], self.roi_dict['start_x']),
    #     #                                    (self.roi_dict['start_y'] + self.roi_dict['tail_length_y'],
    #     #                                     self.roi_dict['start_x'] + self.roi_dict['tail_length_x'])))

    # def send_roi_to_queue(self):
    #     self.tail_start_points_queue.put(self.get_tracking_params())

    # def get_tracking_params(self):
    #     # Invert x and y:
    #     handle_pos = self.roi_tail.getSceneHandlePositions()
    #     try:
    #         p1 = self.display_area.mapSceneToView(handle_pos[0][1])
    #         p2 = self.display_area.mapSceneToView(handle_pos[1][1])
    #         self.roi_dict['start_y'] = p1.x()
    #         self.roi_dict['start_x'] = p1.y()  # start x
    #         self.roi_dict['tail_length_y'] = p2.x() - p1.x()  # delta y
    #         self.roi_dict['tail_length_x'] = p2.y() - p1.y()  # delta x
    #
    #         self.tracking_params.update(self.roi_dict)
    #
    #     except np.linalg.LinAlgError:
    #         print('tracking parameters not received yet')
    #     return self.tracking_params
    #
    # def update_image(self):
    #     super().update_image()
    #     if len(self.tail_position_data.stored_data) > 1:
    #         angles = self.tail_position_data.stored_data[-1][2:]
    #         start_x = self.roi_dict['start_x']
    #         start_y = self.roi_dict['start_y']
    #         tail_len_x = self.roi_dict['tail_length_x']
    #         tail_len_y = self.roi_dict['tail_length_y']
    #         tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)
    #         # Get segment length:
    #         tail_segment_length = tail_length / (len(angles) - 1)
    #         points = [np.array([start_x, start_y])]
    #         for angle in angles:
    #             points.append(points[-1] + tail_segment_length * np.array(
    #                 [np.sin(angle), np.cos(angle)]))
    #         points = np.array(points)
    #         self.tail_curve.setData(x=points[:, 1], y=points[:, 0])


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
#
#
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    a = pg.LineSegmentROI((10, 2), (3, 2))
    b,c = a.getHandles()
    b.setPos(QPointF(3,2))
    print(b.x())
#     from multiprocessing import Queue
#     from PyQt5.QtWidgets import QApplication
#     app = QApplication([])
#     q = Queue()
#     for i in range(100):
#         q.put(np.random.randint(0, 255, (640, 480), dtype=np.uint8))
#
#     w = CameraTailSelection(q, 'b')
#     w.show()
#     app.exec_()
