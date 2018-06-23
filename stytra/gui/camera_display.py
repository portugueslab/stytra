import datetime
from queue import Empty

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QRectF, QPointF, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, \
    QCheckBox, QLabel
from pyqtgraph.parametertree import ParameterTree
from skimage.io import imsave

from stytra.hardware.video import CameraControlParameters
from stytra.utilities import prepare_json


class SimpleCameraViewWWidget(QWidget):
    """Core of a widget to stream images from a camera or a video source.
    It does not require a :class:Experiment <stytra.Experiment> to run.
    
    # TODO implement this

    Parameters
    ----------

    Returns
    -------

    """


class CameraViewWidget(QWidget):
    """A widget to show images from a frame source and display the camera controls.
    
    ***It does not implement a frame dispatcher by itself so it may lag behind
    the camera at high frame rates!***

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, experiment=None, camera=None):
        """
        :param experiment: experiment to which this belongs
                           (:class:Experiment <stytra.Experiment> object)
        """

        super().__init__()

        self.experiment = experiment
        if experiment is not None:
            self.camera = experiment.camera
            experiment.gui_timer.timeout.connect(self.update_image)
        else:
            self.camera = camera
            self.gui_timer = QTimer()
            self.gui_timer.setSingleShot(False)

        self.control_params = CameraControlParameters()

        # Create the layout for the camera view:
        self.camera_display_widget = pg.GraphicsLayoutWidget()

        # Display area for showing the camera image:
        self.display_area = pg.ViewBox(lockAspect=1, invertY=False)
        self.display_area.setRange(QRectF(0, 0, 640, 640), update=True,
                                   disableAutoRange=True)
        # Image to which the frame will be set, initially black:
        self.image_item = pg.ImageItem()
        self.image_item.setImage(np.zeros((640, 480), dtype=np.uint8))
        self.display_area.addItem(self.image_item)

        self.camera_display_widget.addItem(self.display_area)

        # Queue of frames coming from the camera
        if hasattr(experiment, 'frame_dispatcher'):
            self.frame_queue = self.experiment.frame_dispatcher.gui_queue
        else:
            self.frame_queue = self.camera.frame_queue

        # Queue of control parameters for the camera:
        self.control_queue = self.camera.control_queue
        self.camera_rotation = self.camera.rotation

        self.camera_params_tree = ParameterTree(showHeader=False)

        # Connect changes in the camera parameters:
        for c in self.control_params.params.children():
            c.sigValueChanged.connect(self.update_controls)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.camera_display_widget)

        self.layout_control = QHBoxLayout()
        if self.control_queue is not None:
            self.params_button = QPushButton('Camera params')
            self.params_button.clicked.connect(self.show_params_gui)
            self.layout_control.addWidget(self.params_button)

        self.captureButton = QPushButton('Capture frame')
        self.captureButton.clicked.connect(self.save_image)
        self.layout_control.addWidget(self.captureButton)

        self.layout.addLayout(self.layout_control)
        self.current_image = None

        self.setLayout(self.layout)

    def update_controls(self, value):
        """

        Parameters
        ----------
        value :
            Parameter object that have changed

        Returns
        -------

        """
        # Put in the queue tuple with name and new value of the parameter:
        self.control_queue.put((value.name(), value.value()))

    def update_image(self):
        """Update displayed frame while emptying frame source queue. This is done
        through a while loop that takes all available frames at every update.
        
        # TODO fix this somehow?
        
        **Important!** if the input queue is too fast this will produce an
        infinite loop and block the interface!

        Parameters
        ----------

        Returns
        -------

        """

        first = True
        while True:
            try:
                # In this way, the frame displayed is actually the most
                # recent one added to the queue, as a queue is FILO:
                if first:
                    time, self.current_image = self.frame_queue.get(
                        timeout=0.0001)
                    first = False
                else:
                    # Else, get to free the queue:
                    _, _ = self.frame_queue.get(timeout=0.001)

            except Empty:
                break

        # Once obtained current image, display it:
        if self.current_image is not None:
            self.image_item.setImage(self.current_image)

    def save_image(self):
        """Save a frame to the current directory."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        imsave(self.experiment.directory + '/' + timestamp + '_img.png',
               self.image_item.image)

    def show_params_gui(self):
        """ """
        self.camera_params_tree.setParameters(self.control_params.params)
        self.camera_params_tree.show()
        self.camera_params_tree.setWindowTitle('Camera parameters')
        self.camera_params_tree.resize(450, 600)


class CameraSelection(CameraViewWidget):
    """Generic class to overlay on video an ROI that can be
    used to select regions of the image and communicate their position to the
    tracking algorithm (e.g., tail starting point or eyes region).
    
    The changes of parameters read through the ROI position are handled
    via the track_params class, so they must have a corresponding entry in the
    definition of the FrameProcessingMethod of the tracking function of choice.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Redefine the source of the displayed images to be the FrameProcessor
        # output queue:
        self.frame_queue = self.experiment.frame_dispatcher.gui_queue
        self.track_params = self.experiment.tracking_method.params

        # Redefine the source of the displayed images to be the FrameProcessor
        # output queue:
        self.frame_queue = self.experiment.frame_dispatcher.gui_queue

        # Get the tracking parameters from the experiment class and connect
        # their change signal to update ROI position:
        self.track_params = self.experiment.tracking_method.params
        self.track_params.sigTreeStateChanged.connect(self.set_pos_from_tree)

    def initialise_roi(self):
        """ROI is initialised separately, so it can first be defined in the
        child __init__.

        Parameters
        ----------

        Returns
        -------

        """
        try:
            # Add ROI to image and connect it to the function for updating
            # the relative params:
            self.display_area.addItem(self.roi)
            self.roi.sigRegionChangeFinished.connect(self.set_pos_from_roi)
        except AttributeError:
            print('No ROI defined in CameraSelection child')

    def set_pos_from_tree(self):
        """Called when ROI position values are changed in the ParameterTree.
        Change the position of the displayed ROI:

        Parameters
        ----------

        Returns
        -------

        """
        pass

    def set_pos_from_roi(self):
        """Called when ROI position values are changed in the displayed ROI.
        Change the position in the ParameterTree values.

        Parameters
        ----------

        Returns
        -------

        """
        pass


class CameraTailSelection(CameraSelection):
    """Widget for select tail pts and monitoring tracking in embedded fish."""
    def __init__(self, **kwargs):
        """
        :param experiment:  experiment in which it is used.

        """

        super().__init__(**kwargs)

        # Draw ROI for tail selection:
        self.roi = pg.LineSegmentROI((self.track_params['tail_start'],
                                     (self.track_params['tail_start'][0] +
                                      self.track_params['tail_length'][0],
                                      self.track_params['tail_start'][1] +
                                      self.track_params['tail_length'][1])),
                                     pen=dict(color=(230, 40, 5),
                                              width=3))
        self.initialise_roi()

        # Prepare curve for plotting tracked tail position:
        self.tail_curve = pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                    width=3))
        self.display_area.addItem(self.tail_curve)

    def set_pos_from_tree(self):
        """Go to parent for definition."""
        p1, p2 = self.roi.getHandles()
        p1.setPos(QPointF(*self.track_params['tail_start']))
        p2.setPos(QPointF(self.track_params['tail_start'][0] +
                          self.track_params['tail_length'][0],
                          self.track_params['tail_start'][1] +
                          self.track_params['tail_length'][1]))

    def set_pos_from_roi(self):
        """Go to parent for definition."""
        p1, p2 = self.roi.getHandles()
        with self.track_params.treeChangeBlocker():
            self.track_params.param('tail_start').setValue((
                p1.x(), p1.y()))
            self.track_params.param('tail_length').setValue((
                p2.x() - p1.x(), p2.y() - p1.y()))

    def update_image(self):
        """Go to parent for definition."""
        super().update_image()

        # Check for data to be displayed:
        if len(self.experiment.data_acc.stored_data) > 1:
            # Retrieve tail angles from tail:
            angles = self.experiment.data_acc.stored_data[-1][2:]

            # Get tail position and length from the parameters:
            start_x = self.track_params['tail_start'][1]
            start_y = self.track_params['tail_start'][0]
            tail_len_x = self.track_params['tail_length'][1]
            tail_len_y = self.track_params['tail_length'][0]
            tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)

            # Get segment length:
            tail_segment_length = tail_length / (len(angles) - 1)
            points = [np.array([start_x, start_y])]

            # Calculate tail points from angles and position:
            for angle in angles:
                points.append(points[-1] + tail_segment_length * np.array(
                    [np.sin(angle), np.cos(angle)]))
            points = np.array(points)
            self.tail_curve.setData(x=points[:, 1], y=points[:, 0])


class CameraEyesSelection(CameraSelection):
    """
    Widget for select tail pts and monitoring tracking in embedded fish.
    """
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        # Draw ROI for eyes region selection:
        self.roi = pg.ROI(pos=self.track_params['wnd_pos'],
                          size=self.track_params['wnd_dim'],
                          pen=dict(color=(230, 40, 5),
                                   width=3))

        self.roi.addScaleHandle([0, 0], [1, 1])
        self.roi.addScaleHandle([1, 1], [0, 0])

        self.initialise_roi()

        self.curves_eyes = [pg.EllipseROI(pos=(0, 0), size=(10, 10),
                                          movable=False,
                                          pen=dict(color=k, width=3))
                            for k in [(5, 40, 230), (40, 230, 5)]]

        self.pre_th = [0, 0]

        for c in self.curves_eyes:
            self.display_area.addItem(c)
            [c.removeHandle(h) for h in c.getHandles()]

        self.tgl_threshold_view = QCheckBox()
        self.lbl_threshold_view = QLabel('View thresholded image')
        self.layout_control.addWidget(self.tgl_threshold_view)
        self.layout_control.addWidget(self.lbl_threshold_view)

    def set_pos_from_tree(self):
        """Go to parent for definition."""
        self.roi.setPos(self.track_params['wnd_pos'], finish=False)
        self.roi.setSize(self.track_params['wnd_dim'])

    def set_pos_from_roi(self):
        """Go to parent for definition."""
        # Set values in the ParameterTree:
        with self.track_params.treeChangeBlocker():
            self.track_params.param('wnd_dim').setValue(tuple(
                [int(p) for p in self.roi.size()]))
            self.track_params.param('wnd_pos').setValue(tuple(
                [int(p) for p in self.roi.pos()]))

    def update_image(self):
        """Go to parent for definition."""
        super().update_image()
        im = self.current_image

        # In this widget a toggle button allows the user to see the
        # thresholded image used by the ellipse fitting function:
        if self.tgl_threshold_view.isChecked():
            im = (im < self.track_params['threshold']).astype(np.uint8)

        if len(self.experiment.data_acc.stored_data) > 1:
            e = self.experiment.data_acc.stored_data[-1][1:]
            for i, o in enumerate([0, 5]):
                if e[0] == e[0]:
                    for ell, col in zip(self.curves_eyes, [(5, 40, 230),
                                                           (40, 230, 5)]):
                        ell.setPen(col, width=3)

                    pos = self.track_params['wnd_pos']

                    # This long annoying part take care of the calculation
                    # of rotation and translation for the ROI starting from
                    # ellipse center, axis and rotation.
                    # Some geometry is required because pyqtgraph rotation
                    # happens around lower corner and not
                    # around center.
                    th = - e[o + 4]  # eye angle from tracked ellipse
                    c_x = int(e[o + 2] / 2)  # ellipse center x and y
                    c_y = int(e[o + 3] / 2)

                    if c_x != 0 and c_y != 0:
                        th_conv = th * (np.pi/180)  # in radiants now

                        # rotate based on different from previous angle:
                        self.curves_eyes[i].rotate(th - self.pre_th[i])

                        # Angle and rad of center point from left lower corner:
                        c_th = np.arctan(c_x / c_y)
                        c_r = np.sqrt(c_x**2 + c_y**2)

                        # Coords of the center after rotation around left lower
                        # corner, to be corrected when setting position:
                        center_after = (np.sin(c_th + th_conv)*c_r,
                                        np.cos(c_th + th_conv)*c_r)

                        # Calculate pos for eye ROIs. This require correction
                        # for the box position, for the ellipse dimensions and
                        # for the rotation around corner instead of center.
                        self.curves_eyes[i].setPos(
                             e[o + 1] + pos[0] - c_x + (c_x - center_after[1]),
                             e[o + 0] + pos[1] - c_y + (c_y - center_after[0]))
                        self.curves_eyes[i].setSize((c_y * 2, c_x * 2))

                        self.pre_th[i] = th

                else:
                    # No eyes detected:
                    for ell in self.curves_eyes:
                        ell.setPen(None)

        self.image_item.setImage(im)


class CameraViewCalib(CameraViewWidget):
    """ """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.points_calib = pg.ScatterPlotItem()
        self.display_area.addItem(self.points_calib)

    def show_calibration(self, calibrator):
        """

        Parameters
        ----------
        calibrator :
            

        Returns
        -------

        """
        if calibrator.proj_to_cam is not None:
            camera_points = np.pad(calibrator.points, ((0, 0), (0, 1)),
                                   mode='constant', constant_values=1) @ calibrator.proj_to_cam.T

            points_dicts = []
            for point in camera_points:
                xn, yn = point[::-1]
                points_dicts.append(dict(x=xn, y=yn, size=8,
                                         brush=(210, 10, 10)))

            self.points_calib.setData(points_dicts)

