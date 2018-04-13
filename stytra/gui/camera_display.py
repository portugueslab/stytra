import datetime
from multiprocessing import Queue
from queue import Empty

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from pyqtgraph.parametertree import ParameterTree
from skimage.io import imsave

from stytra.hardware.video import CameraControlParameters


class CameraViewWidget(QWidget):
    def __init__(self, experiment):
        """
        A widget to show the camera and display the controls
        :param experiment: experiment to which this belongs
        """

        super().__init__()

        self.control_params = CameraControlParameters()

        self.camera_queue = Queue()  # What is this?
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

        # Queue of frames coming from the camera
        self.frame_queue = self.camera.frame_queue
        # Queue of control parameters for the camera
        self.control_queue = self.camera.control_queue
        self.camera_rotation = self.camera.rotation
        experiment.gui_timer.timeout.connect(self.update_image)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.protocol_params_tree = ParameterTree(showHeader=False)
        self.control_params.params.sigTreeStateChanged.connect(
            self.update_controls)

        self.layout.addWidget(self.camera_display_widget)
        if self.control_queue is not None:
            self.params_button = QPushButton('Camera params')
            self.params_button.clicked.connect(self.show_params_gui)
            self.layout.addWidget(self.params_button)

        self.captureButton = QPushButton('Capture frame')
        self.captureButton.clicked.connect(self.save_image)
        self.layout.addWidget(self.captureButton)
        self.current_image = None

        self.setLayout(self.layout)

    def update_controls(self):
        self.control_queue.put(self.control_params.get_clean_values())

    def update_image(self):
        first = True
        while True:
            try:
                if first:
                    time, self.current_image = self.frame_queue.get(
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
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        imsave(self.experiment.directory + '/' + timestamp + '_img.png',
               self.image_item.image)

    def show_params_gui(self):
        self.protocol_params_tree.setParameters(self.control_params.params)
        self.protocol_params_tree.show()
        self.protocol_params_tree.setWindowTitle('Camera parameters')
        self.protocol_params_tree.resize(450, 600)


class CameraTailSelection(CameraViewWidget):
    def __init__(self, experiment, **kwargs):
        """ Widget for select tail pts and monitoring tracking in embedded fish.
        :param tail_start_points_queue: queue where to dispatch tail points
        :param tail_position_data: DataAccumulator object for tail pos data.
        :param roi_dict: dictionary for setting default tail position
        """
        self.tail_position_data = Queue()  # tail_position_data
        super().__init__(experiment,  **kwargs)
        self.tail_start_points_queue = Queue()  # tail_start_points_queue

        # Redefine the source of the displayed images to be the FrameProcessor
        # output queue:
        self.frame_queue = self.experiment.frame_dispatcher.gui_queue

        self.track_params = self.experiment.tracking_method.params
        # Draw ROI for tail selection:
        self.roi_tail = pg.LineSegmentROI((self.track_params['tail_start'],
                                          (self.track_params['tail_start'][0] +
                                           self.track_params['tail_length'][0],
                                           self.track_params['tail_start'][1] +
                                           self.track_params['tail_length'][1])
                                           ),
                                          pen=dict(color=(230, 40, 5),
                                                   width=3))

        self.tail_curve = pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                    width=3))
        self.display_area.addItem(self.tail_curve)
        self.display_area.addItem(self.roi_tail)

        self.roi_tail.sigRegionChangeFinished.connect(self.set_param_val)
        self.track_params.sigTreeStateChanged.connect(self.set_roi)

    def set_roi(self):
        p1, p2 = self.roi_tail.getHandles()
        p1.setPos(QPointF(*self.track_params['tail_start']))
        p2.setPos(QPointF(self.track_params['tail_start'][0] +
                          self.track_params['tail_length'][0],
                          self.track_params['tail_start'][1] +
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


class CameraEyesSelection(CameraViewWidget):
    def __init__(self, experiment, **kwargs):
        """ Widget for select tail pts and monitoring tracking in embedded fish.
        :param tail_start_points_queue: queue where to dispatch tail points
        :param tail_position_data: DataAccumulator object for tail pos data.
        :param roi_dict: dictionary for setting default tail position
        """
        self.queue_eyes_position_data = Queue()
        super().__init__(experiment,  **kwargs)
        self.queue_eyes_square = Queue()

        # Redefine the source of the displayed images to be the FrameProcessor
        # output queue:
        self.queue_frame = self.experiment.frame_dispatcher.frame_queue

        self.params_eyes_track = self.experiment.tracking_method.params

        # Draw ROI for tail selection:
        self.roi_eyes = pg.ROI(pos=self.params_eyes_track['wnd_pos'],
                               size=self.params_eyes_track['wnd_dim'],
                               pen=dict(color=(230, 40, 5),
                                        width=3))

        self.roi_eyes.addScaleHandle([0, 0], [1, 1])
        self.roi_eyes.addScaleHandle([1, 1], [0, 0])
        self.display_area.addItem(self.roi_eyes)

        # Prepare curve for displaying the eyes:
        self.curves_eyes = [pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                      width=3))]
        for c in self.curves_eyes:
            self.display_area.addItem(c)

        # Connect signals for modifying the tracking parameters
        self.roi_eyes.sigRegionChangeFinished.connect(self.set_pos_from_roi)
        self.params_eyes_track.sigTreeStateChanged.connect(self.set_pos_from_tree)

    def set_pos_from_tree(self):
        """ Called when ROI position values are changed in the ParameterTree.
        Change the position of the displayed ROI:
        """
        self.roi_eyes.setPos(self.params_eyes_track['wnd_pos'], finish=False)
        self.roi_eyes.setSize(self.params_eyes_track['wnd_dim'])

    def set_pos_from_roi(self):
        """ Called when ROI position values are changed in the displayed ROI.
        Change the position in the ParameterTree values.
        """

        # Set values in the ParameterTree:
        with self.params_eyes_track.treeChangeBlocker():
            self.params_eyes_track.param('wnd_dim').setValue(tuple(
                [int(p) for p in self.roi_eyes.size()]))
            self.params_eyes_track.param('wnd_pos').setValue(tuple(
                [int(p) for p in self.roi_eyes.pos()]))

    def update_image(self):
        super().update_image()

        # if len(self.experiment.data_acc_eyes_angles.stored_data) > 1:
        #     angles = self.experiment.data_acc_tailpoints.stored_data[-1][:2]
        #     start_x = self.track_params['tail_start'][1]
        #     start_y = self.track_params['tail_start'][0]
        #     tail_len_x = self.track_params['tail_length'][1]
        #     tail_len_y = self.track_params['tail_length'][0]
        #     tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)
        #
        #     # Get segment length:
        #     tail_segment_length = tail_length / (len(angles) - 1)
        #     points = [np.array([start_x, start_y])]
        #     for angle in angles:
        #         points.append(points[-1] + tail_segment_length * np.array(
        #             [np.sin(angle), np.cos(angle)]))
        #     points = np.array(points)
        #     self.tail_curve.setData(x=points[:, 1], y=points[:, 0])


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

