import datetime
from queue import Empty

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QRectF, QPointF, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from skimage.io import imsave
from numba import jit
from math import sin, cos
from lightparam.gui import ParameterGui, ControlToggleIcon

from stytra.gui.buttons import IconButton, ToggleIconButton, get_icon


class SingleLineROI(pg.LineSegmentROI):
    """ Subclassing pyqtgraph polyLineROI to remove the "add handle" behavior.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.translatable = False

    def segmentClicked(self):
        pass


class CameraViewWidget(QWidget):
    """A widget to show images from a frame source and display the camera controls.


    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, experiment=None, **kwargs):
        """
        :param experiment: experiment to which this belongs
                           (:class:Experiment <stytra.Experiment> object)
        """

        super().__init__(*args, **kwargs)

        self.experiment = experiment
        if experiment is not None:
            self.camera = experiment.camera
            experiment.gui_timer.timeout.connect(self.retrieve_image)
        else:
            self.gui_timer = QTimer()
            self.gui_timer.setSingleShot(False)

        self.control_params = self.experiment.camera_state

        # Create the layout for the camera view:
        self.camera_display_widget = pg.GraphicsLayoutWidget()

        # Display area for showing the camera image:
        self.display_area = pg.ViewBox(lockAspect=1, invertY=False)
        self.display_area.setRange(
            QRectF(0, 0, 640, 480), update=True, disableAutoRange=True
        )
        self.scale = 640

        self.display_area.invertY(True)
        # Image to which the frame will be set, initially black:
        self.image_item = pg.ImageItem()
        self.image_item.setImage(np.zeros((640, 480), dtype=np.uint8))
        self.display_area.addItem(self.image_item)

        self.camera_display_widget.addItem(self.display_area)

        # Queue of frames coming from the camera
        if hasattr(experiment, "frame_dispatcher"):
            self.frame_queue = self.experiment.frame_dispatcher.gui_queue
        else:
            self.frame_queue = self.camera.frame_queue

        # Queue of control parameters for the camera:
        self.control_queue = self.camera.control_queue
        self.camera_rotation = self.camera.rotation

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.camera_display_widget)

        self.layout_control = QHBoxLayout()
        self.layout_control.setContentsMargins(10, 0, 10, 10)

        self.btn_pause = ControlToggleIcon(
            self.experiment.camera_state,
            "paused",
            icon_on=get_icon("play"),
            icon_off=get_icon("pause"),
            action_off="Pause",
            action_on="Play",
        )
        self.layout_control.addWidget(self.btn_pause)

        if hasattr(self.experiment.camera_state, "replay"):
            self.experiment.camera_state.replay = False

            self.btn_rewind = ControlToggleIcon(
                self.experiment.camera_state,
                "replay",
                icon_on=get_icon("rewind"),
                action_off="Resume",
                action_on="Replay",
            )
            self.layout_control.addWidget(self.btn_rewind)

        if self.control_queue is not None:
            self.btn_camera_param = IconButton(
                icon_name="edit_camera", action_name="Configure camera"
            )
            self.btn_camera_param.clicked.connect(self.show_params_gui)
            self.layout_control.addWidget(self.btn_camera_param)

        self.btn_capture = IconButton(
            icon_name="camera_flash", action_name="Capture frame"
        )
        self.btn_capture.clicked.connect(self.save_image)
        self.layout_control.addWidget(self.btn_capture)

        self.btn_autorange = ToggleIconButton(
            icon_off="autoscale", icon_on="autoscaleOFF", action_on="Autoscale"
        )
        self.layout_control.addWidget(self.btn_autorange)

        self.layout.addLayout(self.layout_control)
        self.current_image = None

        self.setLayout(self.layout)
        self.current_frame_time = None

        self.param_widget = None

    def retrieve_image(self):
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
                    qr = self.frame_queue.get(timeout=0.0001)
                    self.current_image = qr[-1]
                    self.current_frame_time = qr[0]
                    # first = False
                else:
                    # Else, get to free the queue:
                    _, _ = self.frame_queue.get(timeout=0.001)
            except Empty:
                break

        # Once obtained current image, display it:
        if self.isVisible():
            if self.current_image is not None:
                if self.current_image.shape[0] != self.scale:
                    self.scale = self.current_image.shape[0]
                    self.scale_changed()
                    self.display_area.setRange(
                        QRectF(0, 0, self.current_image.shape[1],
                               self.current_image.shape[0]), update=True,
                        disableAutoRange=True
                    )
                self.image_item.setImage(
                    self.current_image, autoLevels=self.btn_autorange.isChecked()
                )

    def scale_changed(self):
        self.display_area.setRange(
            QRectF(0, 0, self.current_image.shape[1],
                   self.current_image.shape[0]),
            update=True, disableAutoRange=True
        )

    def save_image(self, name=None):
        """Save a frame to the current directory."""
        if name is None or not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = self.experiment.filename_base() + timestamp + "_img.png"
        imsave(name, self.image_item.image)

    def show_params_gui(self):
        """ """
        self.param_widget = ParameterGui(self.control_params)
        self.param_widget.show()


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

    def initialise_roi(self, roi):
        """ROI is initialised separately, so it can first be defined in the
        child __init__.

        Parameters
        ----------

        Returns
        -------

        """
        # Add ROI to image and connect it to the function for updating
        # the relative params:
        self.display_area.addItem(roi)
        roi.sigRegionChanged.connect(self.set_pos_from_roi)

    def set_pos_from_tree(self):
        """Called when ROI position values are changed in the ParameterTree.
        Change the position of the displayed ROI.

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


class TailTrackingSelection(CameraSelection):
    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)

        # Draw ROI for tail selection:
        self.tail_params = self.experiment.pipeline.tailtrack._params
        self.roi_tail = SingleLineROI(
            self.tail_points(),
            pen=dict(color=(40, 5, 200), width=3),
        )

        # Prepare curve for plotting tracked tail position:
        self.curve_tail = pg.PlotCurveItem(pen=dict(color=(230, 40, 5),
                                                    width=3))
        self.display_area.addItem(self.curve_tail)

        self.initialise_roi(self.roi_tail)

        self.setting_param_val = False

    def set_pos_from_tree(self):
        """Go to parent for definition."""
        super().set_pos_from_tree()
        if not self.setting_param_val:
            self.roi_tail.prepareGeometryChange()
            p1, p2 = self.roi_tail.getHandles()
            np1, np2 = self.tail_points()
            p1.setPos(QPointF(*np1))
            p2.setPos(QPointF(*np2))

    def set_pos_from_roi(self):
        """Go to parent for definition."""
        super().set_pos_from_roi()

        self.setting_param_val = True

        p1, p2 = self.roi_tail.getHandles()
        self.tail_params.tail_start = (p1.y()/self.scale,
                                       p1.x()/self.scale)
        self.tail_params.params.tail_start.changed = True
        self.tail_params.tail_length = ((p2.y() - p1.y())/self.scale,
                                        (p2.x() - p1.x())/self.scale)
        self.tail_params.params.tail_length.changed = True

        self.setting_param_val = False

    def scale_changed(self):
        self.set_pos_from_tree()

    def retrieve_image(self):
        """Go to parent for definition."""
        super().retrieve_image()

        if self.current_image is None:
            return

        # Get data from queue(first is timestamp)
        if len(self.experiment.acc_tracking.stored_data) > 1:
            # To match tracked points and frame displayed looks for matching
            # timestamps from the two different queues:
            retrieved_data = self.experiment.acc_tracking.values_at_abs_time(self.current_frame_time)
            # Check for data to be displayed:
            # Retrieve tail angles from tail

            angles = [getattr(retrieved_data, "theta_{:02d}".format(i))
                      for i in range(self.tail_params.n_output_segments)]
            # Get tail position and length from the parameters:
            (start_y, start_x), (tail_len_y, tail_len_x) = self.tail_dims()
            tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)

            # Get segment length:
            tail_segment_length = tail_length / (len(angles))
            points = [np.array([start_x, start_y])]

            # Calculate tail points from angles and position:
            for angle in angles:
                points.append(
                    points[-1]
                    + tail_segment_length * np.array([np.cos(angle), np.sin(angle)])
                )
            points = np.array(points)
            self.curve_tail.setData(x=points[:, 1], y=points[:, 0])

    def tail_points(self):
        tsy, tsx = (t * self.scale for t in self.tail_params.tail_start)
        tly, tlx = (t * self.scale for t in self.tail_params.tail_length)
        return (tsx, tsy), (tsx+tlx, tsy+tly)

    def tail_dims(self):
        tsy, tsx = (t * self.scale for t in self.tail_params.tail_start)
        tly, tlx = (t * self.scale for t in self.tail_params.tail_length)
        return (tsx, tsy), (tlx, tly)


class EyeTrackingSelection(CameraSelection):
    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)

        # Draw ROI for eyes region selection:
        self.pre_th = [0, 0]

        self.eye_params = self.experiment.pipeline.eyetrack._params
        self.roi_eyes = pg.ROI(
            pos=self.eye_params.wnd_pos,
            size=self.eye_params.wnd_dim,
            pen=dict(color=(5, 40, 200), width=3),
        )

        self.roi_eyes.addScaleHandle([0, 0], [1, 1])
        self.roi_eyes.addScaleHandle([1, 1], [0, 0])

        self.curves_eyes = [
            pg.EllipseROI(
                pos=(0, 0), size=(10, 10), movable=False, pen=dict(color=k, width=3)
            )
            for k in [(5, 40, 230), (40, 230, 5)]
        ]

        for c in self.curves_eyes:
            self.display_area.addItem(c)
            [c.removeHandle(h) for h in c.getHandles()]

        self.initialise_roi(self.roi_eyes)

        self.setting_param_val = False

    def set_pos_from_tree(self):
        """Go to parent for definition."""
        super().set_pos_from_tree()
        if not self.setting_param_val:
            self.roi_eyes.setPos(self.eye_params.wnd_pos, finish=False)
            self.roi_eyes.setSize(self.eye_params.wnd_dim)

    def set_pos_from_roi(self):
        """Go to parent for definition."""
        super().set_pos_from_roi()
        self.setting_param_val = True
        self.eye_params.params.wnd_dim.changed = True
        self.eye_params.wnd_dim = tuple([int(p) for p in self.roi_eyes.size()])
        self.eye_params.params.wnd_pos.changed = True
        self.eye_params.wnd_pos = tuple([int(p) for p in self.roi_eyes.pos()])
        self.setting_param_val = False

    def scale_changed(self):
        self.set_pos_from_tree()

    def retrieve_image(self):
        """Go to parent for definition."""
        super().retrieve_image()

        if self.current_image is None:
            return

        # Get data from queue(first is timestamp)
        if len(self.experiment.acc_tracking.stored_data) > 1:
            # To match tracked points and frame displayed looks for matching
            # timestamps from the two different queues:
            retrieved_data = self.experiment.acc_tracking.values_at_abs_time(self.current_frame_time)
            # Check for data to be displayed:

            if len(self.experiment.acc_tracking.stored_data) > 1:
                self.roi_eyes.setPen(dict(color=(5, 40, 200), width=3))
                checkifnan = getattr(retrieved_data, "th_e0")
                for i, o in enumerate([0, 5]):
                    if checkifnan == checkifnan:
                        for ell, col in zip(
                            self.curves_eyes, [(5, 40, 230), (40, 230, 5)]
                        ):
                            ell.setPen(col, width=3)

                        pos = self.eye_params.wnd_pos

                        # This long annoying part take care of the calculation
                        # of rotation and translation for the ROI starting from
                        # ellipse center, axis and rotation.
                        # Some geometry is required because pyqtgraph rotation
                        # happens around lower corner and not
                        # around center.
                        # Might be improved with matrix transforms!
                        th = -getattr(retrieved_data, "th_e{}".format(i))  # eye angle from tracked ellipse
                        c_x = int(getattr(retrieved_data, "dim_x_e{}".format(i)) / 2)  # ellipse center x and y
                        c_y = int(getattr(retrieved_data, "dim_y_e{}".format(i)) / 2)

                        if c_x != 0 and c_y != 0:
                            th_conv = th * (np.pi / 180)  # in radiants now

                            # rotate based on different from previous angle:
                            self.curves_eyes[i].rotate(th - self.pre_th[i])

                            # Angle and rad of center point from left lower corner:
                            c_th = np.arctan(c_x / c_y)
                            c_r = np.sqrt(c_x ** 2 + c_y ** 2)

                            # Coords of the center after rotation around left lower
                            # corner, to be corrected when setting position:
                            center_after = (
                                np.sin(c_th + th_conv) * c_r,
                                np.cos(c_th + th_conv) * c_r,
                            )

                            # Calculate pos for eye ROIs. This require correction
                            # for the box position, for the ellipse dimensions and
                            # for the rotation around corner instead of center.
                            self.curves_eyes[i].setPos(
                                getattr(retrieved_data, "pos_y_e{}".format(i))
                                + pos[0] - c_x + (c_x - center_after[1]),
                                getattr(retrieved_data, "pos_x_e{}".format(i))
                                + pos[1] - c_y + (c_y - center_after[0]),
                            )
                            self.curves_eyes[i].setSize((c_y * 2, c_x * 2))

                            self.pre_th[i] = th

                    else:
                        # No eyes detected:
                        for ell in self.curves_eyes:
                            ell.setPen(None)
                        self.roi_eyes.setPen(dict(color=(230, 40, 5), width=3))


class EyeTailTrackingSelection(TailTrackingSelection, EyeTrackingSelection):
    pass


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
            camera_points = (
                np.pad(
                    calibrator.points,
                    ((0, 0), (0, 1)),
                    mode="constant",
                    constant_values=1,
                )
                @ calibrator.proj_to_cam.T
            )

            points_dicts = []
            for point in camera_points:
                xn, yn = point[::-1]
                points_dicts.append(dict(x=xn, y=yn, size=8, brush=(210, 10, 10)))

            self.points_calib.setData(points_dicts)

    def set_pos_from_tree(self):
        pass


@jit(nopython=True)
def _tail_points_from_coords(coords, seglen):
    """ Computes the tail points from a list obtained from a data accumulator

    Parameters
    ----------
    coords
        per fish, will be x, y, theta, theta_00, theta_01, theta_02...
    n_data_per_fish
        number of coordinate entries per fish
    seglen
        length of a single segment

    Returns
    -------
        xs, ys
        list of coordinates
    """

    xs = []
    ys = []
    angles = np.zeros(coords.shape[1] - 5)
    for i_fish in range(coords.shape[0]):
        xs.append(coords[i_fish, 2])
        ys.append(coords[i_fish, 0])
        angles[0] = coords[i_fish, 4]
        angles[1:] = angles[0] + coords[i_fish, 6:]
        for i, an in enumerate(angles):
            if i > 0:
                xs.append(xs[-1])
                ys.append(ys[-1])

            # for drawing the lines, points need to be repeated
            xs.append(xs[-1] + seglen * sin(an))
            ys.append(ys[-1] + seglen * cos(an))

    return xs, ys


class CameraViewFish(CameraViewCalib):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.points_fish = pg.ScatterPlotItem(
            size=5, pxMode=True, brush=(255, 0, 0), pen=None
        )
        self.lines_fish = pg.PlotCurveItem(
            connect="pairs", pen=pg.mkPen((10, 100, 200), width=3)
        )
        self.display_area.addItem(self.points_fish)
        self.display_area.addItem(self.lines_fish)
        self.tracking_params = self.experiment.pipeline.fishtrack._params

    def retrieve_image(self):
        super().retrieve_image()

        if len(self.experiment.acc_tracking.stored_data) == 0 or \
                self.current_image is None:
            return

        current_data = self.experiment.acc_tracking.values_at_abs_time(
            self.current_frame_time)

        n_fish = self.tracking_params.n_fish_max

        n_data_per_fish = (
            len(current_data) - 1
        ) // n_fish  # the first is time, the last is area
        n_points_tail = self.tracking_params.n_segments
        try:
            retrieved_data = np.array(
                current_data[: -1]  # the -1 if for the diagnostic area
            ).reshape(n_fish, n_data_per_fish)
            valid = np.logical_not(np.all(np.isnan(retrieved_data), 1))
            self.points_fish.setData(
                y=retrieved_data[valid, 2], x=retrieved_data[valid, 0]
            )
            if n_points_tail:
                tail_len = (
                    self.tracking_params.tail_length
                    / self.tracking_params.n_segments
                )
                ys, xs = _tail_points_from_coords(retrieved_data, tail_len)
                self.lines_fish.setData(x=xs, y=ys)
        except ValueError as e:
            pass
