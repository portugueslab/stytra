from itertools import product

import numpy as np
import pims
import qimage2ndarray
from pathlib import Path

from PyQt5.QtCore import QPoint, QRect, QPointF, Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QTransform, QPolygon, QRegion

from stytra.stimulation.stimuli import (
    Stimulus,
    DynamicStimulus,
    InterpolatedStimulus,
    CombinerStimulus,
)
from stytra.stimulation.stimuli.backgrounds import existing_file_background


class VisualStimulus(Stimulus):
    """ Stimulus class to paint programmatically on a canvas.
    For this subclass of Stimulus, their core function (paint()) is
    not called by the ProtocolRunner, but directly from the
    StimulusDisplayWindow. Since a StimulusDisplayWindow is directly linked to
    a ProtocolRunner, at every time the paint() method that is called
    is the one from the correct current stimulus.

    Parameters
    ----------
    clip_mask :
        mask for clipping the stimulus. Unfortunately we cannot pass a QPolygon here,
        se to allow for some flexibility there are some heuristics to figure out the
        clipping shape depending on the argument type and dimensions.
        There's tree possible cases for the mask:
            - **Circular mask**: If `clip_mask` is a single number, or a tuple of three numbers, the
              mask will be a circle.
              - A single number specifies the diameter of the circle,
                in relative screen size units;
              - A tuple of three numbers specifies center x, y and diameter of the circle,
                in  relative screen size units.

            - **Polygon mask**: If `clip_mask` is a list of tuples with 2 elements each, the mask will
              be a polygon that uses the tuples of the list as (x, y) coordinates
              (there should be at least three elements there)

            - **Rectangular mask**: If `clip_mask` is a tuple of four numbers, the mask will be a rectangle
              that interprets the coordinates as (x_pos, y_pos, width, height).

    Returns
    -------

    """

    def __init__(self, *args, clip_mask=None, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)
        self.clip_mask = clip_mask

    def paint(self, p, w, h):
        """Paint function. Called by the StimulusDisplayWindow update method
        (NOT by the `ProtocolRunner.update()` !).

        Parameters
        ----------
        p : QPainter object
            Painter object for drawing
        w :
            width of the display window
        h :
            height of the display window

        Returns
        -------

        """
        pass

    def clip(self, p, w, h):
        """Clip image before painting

        Parameters
        ----------
        p :
            QPainter object used for painting
        w :
            image width
        h :
            image height

        Returns
        -------

        """
        if self.clip_mask is not None:
            if isinstance(self.clip_mask, float):  # centered circle
                a = QRegion(
                    w / 2 - self.clip_mask * w,
                    h / 2 - self.clip_mask * h,
                    self.clip_mask * w * 2,
                    self.clip_mask * h * 2,
                    type=QRegion.Ellipse,
                )
                p.setClipRegion(a)
            elif isinstance(self.clip_mask[0], tuple):  # polygon
                points = [QPoint(int(w * x), int(h * y)) for (x, y) in self.clip_mask]
                p.setClipRegion(QRegion(QPolygon(points)))
            else:
                p.setClipRect(
                    self.clip_mask[0] * w,
                    self.clip_mask[1] * h,
                    self.clip_mask[2] * w,
                    self.clip_mask[3] * h,
                )


class VisualCombinerStimulus(VisualStimulus, CombinerStimulus):
    """
    Class to have two visual stimuli happening pseudo-simultaneously (one update
    still has to be called before the other one).
    """

    def paint(self, p, w, h):
        for s in self._stim_list:
            s.paint(p, w, h)
            # p.end()


class FullFieldVisualStimulus(VisualStimulus):
    """ Class for painting a full field flash of a specific color.

    Parameters
    ----------
    color : (int, int, int) tuple
         color of the full field flash (int tuple)
    """

    def __init__(self, *args, color=(255, 0, 0), **kwargs):
        """ """
        super().__init__(*args, **kwargs)
        self.color = color
        self.name = "flash"

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))  # Use chosen color
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))  # draw full field rectangle


class DynamicLuminanceStimulus(FullFieldVisualStimulus, InterpolatedStimulus):
    """ A luminance stimulus that has dynamically specified luminance.


    Parameters
    ----------

    luminance: float
        a multiplier (0-1) from black to full luminance



    """

    def __init__(self, *args, color=(255, 0, 0), luminance=0.0, **kwargs):
        self.luminance = luminance
        super().__init__(*args, dynamic_parameters=["luminance"], **kwargs)
        self.original_color = np.array(color)
        self.color = color
        self.name = "luminance"

    def update(self):
        super().update()
        self.color = tuple(self.luminance * self.original_color)


class Pause(FullFieldVisualStimulus):
    """ Class for painting full field black stimuli.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = "pause"


class VideoStimulus(VisualStimulus, DynamicStimulus):
    """ Displays videos using PIMS, at a specified framerate.
    """

    def __init__(self, *args, video_path, framerate=None, duration=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = "video"

        self.dynamic_parameters.append("i_frame")
        self.i_frame = 0
        self.video_path = video_path

        self._current_frame = None
        self._last_frame_display_time = 0
        self._video_seq = None

        self.framerate = framerate
        self.duration = duration

    def initialise_external(self, *args, **kwargs):
        super().initialise_external(*args, **kwargs)
        self._video_seq = pims.Video(self._experiment.asset_dir + "/" + self.video_path)

        self._current_frame = self._video_seq.get_frame(self.i_frame)
        try:
            metadata = self._video_seq.get_metadata()

            if self.framerate is None:
                self.framerate = metadata["fps"]
            if self.duration is None:
                self.duration = metadata["duration"]

        except AttributeError:
            if self.framerate is None:
                self.framerate = self._video_seq.frame_rate

            if self.duration is None:
                self.duration = self._video_seq.duration

    def update(self):
        super().update()
        # if the video restarted, it means the last display time
        # is incorrect, it has to be reset
        if self._elapsed < self._last_frame_display_time:
            self._last_frame_display_time = 0
        if self._elapsed >= self._last_frame_display_time + 1 / self.framerate:
            self.i_frame = int(round(self._elapsed * self.framerate))
            next_frame = self._video_seq.get_frame(self.i_frame)
            if next_frame is not None:
                self._current_frame = next_frame
                self._last_frame_display_time = self._elapsed

    def paint(self, p, w, h):
        display_centre = (w / 2, h / 2)
        img = qimage2ndarray.array2qimage(self._current_frame)
        p.drawImage(
            QPoint(
                display_centre[0] - self._current_frame.shape[1] // 2,
                display_centre[1] - self._current_frame.shape[0] // 2,
            ),
            img,
        )


class PositionStimulus(VisualStimulus, DynamicStimulus):
    """Stimulus with a defined position and orientation to the fish.
        """

    def __init__(self, *args, x=0, y=0, theta=0, **kwargs):
        """ """
        self.x = x
        self.y = y
        self.theta = theta
        super().__init__(*args, dynamic_parameters=["x", "y", "theta"], **kwargs)


class BackgroundStimulus(PositionStimulus):
    """Stimulus with a tiling background
        """

    def __init__(self, *args, background_color=(0, 0, 0), **kwargs):
        self.background_color = background_color
        super().__init__(*args, **kwargs)

    def get_unit_dims(self, w, h):
        return w, h

    def get_transform(self, w, h, x, y):
        return QTransform().rotate(self.theta * 180 / np.pi).translate(x, y)

    def get_tile_ranges(self, imw, imh, w, h, tr: QTransform):
        """ Calculates the number of tiles depending on the transform.

        Parameters
        ----------
        imw
        imh
        w
        h
        tr

        Returns
        -------

        """

        # we find where the display surface is in the coordinate system of a single tile
        corner_points = [
            np.array([0.0, 0.0]),
            np.array([w, 0.0]),
            np.array([w, h]),
            np.array([0.0, h]),
        ]
        points_transformed = np.array(
            [tr.inverted()[0].map(*cp) for cp in corner_points]
        )

        # calculate the rectangle covering the transformed display surface
        min_x, min_y = np.min(points_transformed, 0)
        max_x, max_y = np.max(points_transformed, 0)

        # count which tiles need to be drawn
        x_start, x_end = (int(np.floor(min_x / imw)), int(np.ceil(max_x / imw)))
        y_start, y_end = (int(np.floor(min_y / imh)), int(np.ceil(max_y / imh)))

        return range(x_start, x_end + 1), range(y_start, y_end + 1)

    def paint(self, p, w, h):
        if self._experiment.calibrator is not None:
            mm_px = self._experiment.calibrator.mm_px
        else:
            mm_px = 1

        self.clip(p, w, h)

        # draw the black background
        p.setBrush(QBrush(QColor(*self.background_color)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        imw, imh = self.get_unit_dims(w, h)

        dx = self.x / mm_px
        dy = self.y / mm_px

        # rotate the coordinate transform around the position of the fish
        tr = self.get_transform(w, h, dx, dy)
        p.setTransform(tr)

        for idx, idy in product(*self.get_tile_ranges(imw, imh, w, h, tr)):
            self.draw_block(p, QPointF(idx * imw, idy * imh), w, h)

        p.resetTransform()

    def draw_block(self, p, point, w, h):
        """ Has to be defined in each child of the class, defines what
        is to be painted per tile of the repeating stimulus

        Parameters
        ----------
        p :
            
        point :
            
        w :
            
        h :
            

        Returns
        -------

        """
        pass


class CenteredBackgroundStimulus(BackgroundStimulus):
    def get_transform(self, w, h, x, y):
        return (
            QTransform().translate(-w / 2, -h / 2)
            * super().get_transform(w, h, x, y)
            * QTransform().translate(w / 2, h / 2)
        )


class SeamlessImageStimulus(BackgroundStimulus):
    """ Displays an image which should tile seamlessly.

    The top of the image should match with the bottom and the left
    with the right, so there are no discontinuities). An even checkerboard
    works, but with
    some image editing any texture can be adjusted to be seamless.
    """

    def __init__(self, *args, background, background_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "seamless_image"
        self._background = background
        if background_name is not None:
            self.background_name = background_name
        else:
            if isinstance(background, str):
                self.background_name = background
            elif isinstance(background, Path):
                self.background_name = background.name
            else:
                self.background_name = "array {}x{}".format(*self._background.shape)
        self._qbackground = None

    def initialise_external(self, experiment):
        super().initialise_external(experiment)

        # Get background image from folder:
        if isinstance(self._background, str):
            self._qbackground = qimage2ndarray.array2qimage(
                existing_file_background(
                    self._experiment.asset_dir + "/" + self._background
                )
            )
        elif isinstance(self._background, Path):
            self._qbackground = qimage2ndarray.array2qimage(
                existing_file_background(self._background)
            )
        else:
            self._qbackground = qimage2ndarray.array2qimage(self._background)

    def get_unit_dims(self, w, h):
        w, h = self._qbackground.width(), self._qbackground.height()
        return w, h

    def draw_block(self, p, point, w, h):
        p.drawImage(point, self._qbackground)


class GratingStimulus(BackgroundStimulus):
    """ Class for creating a grating pattern by tiling a numpy array that
    defines the stimulus profile. Can be square or sinusoidal.
    For having moving grating stimulus, use subclass MovingGratingStimulus.

    Parameters
    ----------
    grating_angle : float
        fixed angle for the stripes (in radiants)
    grating_period : float
        spatial period of the gratings (in mm)
    grating_col_1 : (int, int, int) tuple
        first color (default=(255, 255, 255))
    grating_col_2 : (int, int, int) tuple
        second color (default=(0, 0, 0))
    """

    def __init__(
        self,
        *args,
        grating_angle=0,
        grating_period=10,
        wave_shape="square",
        grating_col_1=(255,) * 3,
        grating_col_2=(0,) * 3,
        **kwargs
    ):
        super().__init__(*args, background_color=grating_col_2, **kwargs)
        self.theta = grating_angle
        self.grating_period = grating_period
        self.wave_shape = wave_shape
        self.color_1 = grating_col_1
        self.color_2 = grating_col_2
        self._pattern = None
        self._qbackground = None
        self.name = "gratings"

    def create_pattern(self):
        l = max(
            2,
            int(self.grating_period / (max(self._experiment.calibrator.mm_px, 0.0001))),
        )
        if self.wave_shape == "square":
            self._pattern = np.ones((l, 3), np.uint8) * self.color_1
            self._pattern[int(l / 2) :, :] = self.color_2
        elif self.wave_shape == "sine":
            # Define sinusoidally varying weights for the two colors and then
            #  sum them in the pattern
            w = (np.sin(2 * np.pi * np.linspace(1 / l, 1, l)) + 1) / 2

            self._pattern = (
                w[:, None] * np.array(self.color_1)[None, :]
                + (1 - w[:, None]) * np.array(self.color_2)[None, :]
            ).astype(np.uint8)

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.create_pattern()
        # Get background image from folder:
        self._qbackground = qimage2ndarray.array2qimage(self._pattern[None, :, :])

    def get_unit_dims(self, w, h):
        w, h = self._qbackground.width(), self._qbackground.height()
        return w, h

    def draw_block(self, p, point, w, h):
        # Get background image from folder:
        p.drawImage(point, self._qbackground)


class PaintGratingStimulus(BackgroundStimulus):
    """ Class for creating a grating pattern drawing rectangles with PyQt.
    Note that this class does not move
    the grating pattern, to move you need to subclass this together with a dynamic
    stimulus where the x of the gratings is changing (see `MovingGratingStimulus`).

    """

    def __init__(
        self,
        *args,
        grating_angle=0,
        grating_period=10,
        grating_col_1=(255, 255, 255),
        grating_col_2=(0, 0, 0),
        **kwargs
    ):
        """
        :param grating_angle: fixed angle for the stripes
        :param grating_period: spatial period of the gratings (unit?)
        :param grating_color: color for the non-black stripes (int tuple)
        """
        super().__init__(*args, background_color=grating_col_2, **kwargs)
        self.theta = grating_angle
        self.grating_period = grating_period
        self.color = grating_col_1
        self.name = "moving_gratings"
        self.barheight = 100

    def get_unit_dims(self, w, h):
        """
        #TODO what does this thing define?
        """
        return (
            int(self.grating_period / (max(self._experiment.calibrator.mm_px, 0.0001))),
            self.barheight,
        )

    def draw_block(self, p, point, w, h):
        """ Function for drawing the gratings programmatically.
        """
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(*self.color)))
        p.drawRect(
            point.x(),
            point.y(),
            int(
                self.grating_period
                / (2 * max(self._experiment.calibrator.mm_px, 0.0001))
            ),
            self.barheight,
        )


class MovingGratingStimulus(PaintGratingStimulus, InterpolatedStimulus):
    # TODO refactor to cisambiguate
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("x")


class MovingGratingStimulus(PaintGratingStimulus, InterpolatedStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("x")


class HalfFieldStimulus(PositionStimulus):
    """ Phototaxis stimulus which fill half visual field
    with a white background.
    """

    def __init__(
        self, *args, left=False, color=(255, 255, 255), center_dist=0, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.left = left
        self.center_dist = center_dist
        self.color = color
        self.name = "half_field"

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))
        p.setRenderHint(QPainter.Antialiasing)

        points = []
        if self.left:
            dtheta = np.pi / 2
        else:
            dtheta = -np.pi / 2

        theta = self.theta

        sx = (
            self.x
            + h / 2 * np.cos(theta)
            + self.center_dist * np.cos(theta - np.pi / 2)
        )
        sy = (
            self.y
            + h / 2 * np.sin(theta)
            + self.center_dist * np.sin(theta - np.pi / 2)
        )
        points.append(QPoint(sx, sy))
        theta += dtheta

        sx += w * np.cos(theta)
        sy += w * np.sin(theta)
        points.append(QPoint(sx, sy))
        theta += dtheta

        sx += h * np.cos(theta)
        sy += h * np.sin(theta)
        points.append(QPoint(sx, sy))
        theta += dtheta

        sx += w * np.cos(theta)
        sy += w * np.sin(theta)
        points.append(QPoint(sx, sy))
        theta += dtheta

        sx += h * np.cos(theta)
        sy += h * np.sin(theta)
        points.append(QPoint(sx, sy))

        poly = QPolygon(points)
        p.drawPolygon(poly)


class RadialSineStimulus(VisualStimulus):
    """ Circular grating pattern that moves concentrically
    which makes the fish move to the center of the dish.

    """

    def __init__(self, period=8, velocity=5, duration=1, **kwargs):
        super().__init__(**kwargs)
        self.phase = 0
        self.velocity = velocity
        self.duration = duration
        self.period = period
        self.phase = 0
        self.image = None
        self.name = "radial_sine_centering"
        self._dt = 0
        self._past_t = 0

    def update(self):
        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed
        self.phase += self._dt * self.velocity

    def paint(self, p, w, h):
        x, y = (
            (np.arange(d) - d / 2) * self._experiment.calibrator.mm_px for d in (w, h)
        )
        self.image = np.round(
            np.sin(
                np.sqrt((x[None, :] ** 2 + y[:, None] ** 2) * (2 * np.pi / self.period))
                + self.phase
            )
            * 127
            + 127
        ).astype(np.uint8)
        p.drawImage(QPoint(0, 0), qimage2ndarray.array2qimage(self.image))


class FishOverlayStimulus(PositionStimulus):
    """ For testing freely-swimming closed loop, draws a fish in the corresponding
    region on the projector.

    """

    def __init__(self, color=(255, 50, 0), **kwargs):
        super().__init__(**kwargs)
        self.color = color
        self.name = "fish_overlay"

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(self.x, self.y, 3, 3)
        p.setPen(QPen(QColor(*self.color)))
        l = 20
        p.drawLine(
            self.x,
            self.y,
            self.x + np.cos(self.theta) * l,
            self.y + np.sin(self.theta) * l,
        )


def z_func_windmill(x, y, arms):
    """ Function for sinusoidal windmill of arbitrary number of arms
    symmetrical with respect to perpendicular axes (for even n)
    """
    if np.mod(arms, 2) == 0:
        return np.sin(np.arctan((x / y)) * arms + np.pi / 2)
    else:
        return np.cos(np.arctan((x / y)) * arms) * (y < 0).astype(int) + np.cos(
            np.arctan((x / y)) * arms + np.pi
        ) * (y >= 0).astype(int)


class WindmillStimulus(CenteredBackgroundStimulus):
    """ Class for drawing a rotating windmill (radial wedges in alternating colors).
    For moving gratings use subclass

    Parameters
    ----------
    n_arms : int
        number of colored arms of the windmill
    color : (int, int, int) tuple
        color for the non-black stripes (int tuple)

    """

    def __init__(
        self,
        *args,
        color_1=(255,) * 3,
        wave_shape="sinusoidal",
        color_2=(0,) * 3,
        n_arms=8,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.color_1 = color_1
        self.color_2 = color_2
        self.n_arms = n_arms
        self.wave_shape = wave_shape
        self.name = "windmill"
        self._pattern = None
        self._qbackground = None

    def create_pattern(self, side_len=500):
        side_len = side_len * 2
        # Create weights for a windmill to be multiplied by colors:
        x = (np.arange(side_len) - side_len / 2) / side_len
        X, Y = np.meshgrid(x, x)  # grid of points
        W = z_func_windmill(X, Y, self.n_arms)  # evaluation of the function
        W = ((W + 1) / 2)[:, :, np.newaxis]  # normalize and add color axis
        if self.wave_shape == "square":
            W = (W > 0.5).astype(np.uint8)  # binarize for square gratings

        # Multiply by color:
        self._pattern = W * self.color_1 + (1 - W) * self.color_2
        self._qbackground = qimage2ndarray.array2qimage(self._pattern)

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.create_pattern()

    def draw_block(self, p, point, w, h):
        if self._qbackground.height() < h * 1.5 or self._qbackground.width() < w * 1.5:
            self.create_pattern(1.5 * np.max([h, w]))

        point.setX((w - self._qbackground.width()) / 2)
        point.setY((h - self._qbackground.height()) / 2)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.drawImage(point, self._qbackground)


class MovingWindmillStimulus(WindmillStimulus, InterpolatedStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("theta")


class HighResWindmillStimulus(CenteredBackgroundStimulus):
    """Class for drawing a rotating windmill with sharp edges.
    Instead of rotating an image, this class use a painter to draw triangles
    of the windmill at every timestep.
    Compared with the WindmillStimulus class, this windmill has better
    resolution because it avoids distortions and artifacts from image rotation.
    On the other side, it cannot be used for sinusoidal windmill and
    currently does not support a different background color, and takes
    slightly longer to draw the stimulus
    Ideally will be obsolete once the problems of the WindmillStimulus class
    are solved.

    Parameters
    ----------
    n_arms : int
        number of colored arms of the windmill
    color : (int, int, int) tuple
        color for the non-black stripes (int tuple)

    """

    def __init__(self, *args, color=(255,) * 3, n_arms=8, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.n_arms = n_arms
        self.name = "windmill"

    def draw_block(self, p, point, w, h):
        # Painting settings:
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)

        # Here for changing black with another color (to be debugged)
        # p.setBrush(QBrush(QColor(*self.color_2)))
        # # p.drawRect(QRect(-1, -1, (w + 2)*1.5, (h + 2)*1.5))

        p.setBrush(QBrush(QColor(*self.color)))

        # To draw a windmill, a set of consecutive triangles will be painted:
        mid_x = int(w / 2)  # calculate image center
        mid_y = int(h / 2)

        # calculate angles for each triangle:
        angles = np.arange(0, np.pi * 2, (np.pi * 2) / self.n_arms)
        angles += np.pi / 2 + np.pi / (2 * self.n_arms)
        # angular width of the white arms, by default equal to dark ones
        size = np.pi / self.n_arms
        # radius of triangles (much larger than frame)
        rad = (w ** 2 + h ** 2) ** (1 / 2)
        # loop over angles and draw consecutive triangles
        for deg in np.array(angles):
            polyg_points = [
                QPoint(mid_x, mid_y),
                QPoint(int(mid_x + rad * np.cos(deg)), int(mid_y + rad * np.sin(deg))),
                QPoint(
                    int(mid_x + rad * np.cos(deg + size)),
                    int(mid_y + rad * np.sin(deg + size)),
                ),
            ]
            polygon = QPolygon(polyg_points)
            p.drawPolygon(polygon)


class HighResMovingWindmillStimulus(HighResWindmillStimulus, InterpolatedStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("theta")


class CircleStimulus(VisualStimulus, DynamicStimulus):
    """ A filled circle stimulus, which in combination with interpolation
    can be used to make looming stimuli

    Parameters
    ---------
    origin : tuple(float, float)
        positions of the circle centre (as fraction of screen size)

    radius : float
        circle radius (as fraction of screen size)

    backgroud_color : tuple(int, int, int)
        RGB color of the background

    circle_color : tuple(int, int, int)
        RGB color of the circle


    """

    def __init__(
        self,
        *args,
        origin=(0.5, 0.5),
        radius=10,
        background_color=(0, 0, 0),
        circle_color=(255, 255, 255),
        **kwargs
    ):
        super().__init__(*args, dynamic_parameters=["x", "y", "radius"], **kwargs)
        self.x = origin[0]
        self.y = origin[1]
        self.radius = radius
        self.background_color = background_color
        self.circle_color = circle_color
        self.name = "circle"

    def paint(self, p, w, h):
        super().paint(p, w, h)

        # draw the background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.background_color)))
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        # draw the circle
        p.setBrush(QBrush(QColor(*self.circle_color)))
        p.drawEllipse(QPointF(self.x * w, self.y * h), self.radius * w, self.radius * h)


class CalibratedCircleStimulus(VisualStimulus, DynamicStimulus):
    """ A filled circle stimulus, which in combination with interpolation
    can be used to make looming stimuli

    Parameters
    ---------
    origin : tuple(float, float)
        positions of the circle centre (in mm)

    radius : float
        circle radius (in mm)

    backgroud_color : tuple(int, int, int)
        RGB color of the background

    circle_color : tuple(int, int, int)
        RGB color of the circle


    """

    def __init__(
        self,
        *args,
        origin=(0.5, 0.5),
        radius=10,
        background_color=(0, 0, 0),
        circle_color=(255, 255, 255),
        **kwargs
    ):
        super().__init__(*args, dynamic_parameters=["x", "y", "radius"], **kwargs)
        self.x = origin[0]
        self.y = origin[1]
        self.radius = radius
        self.background_color = background_color
        self.circle_color = circle_color
        self.name = "circle"

    def paint(self, p, w, h):
        super().paint(p, w, h)

        if self._experiment.calibrator is not None:
            mm_px = self._experiment.calibrator.mm_px
        else:
            mm_px = 1

        print(mm_px)

        # draw the background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.background_color)))
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        # draw the circle
        p.setBrush(QBrush(QColor(*self.circle_color)))
        p.drawEllipse(QPointF(self.x / mm_px, self.y / mm_px),
                      self.radius / mm_px, self.radius / mm_px)


class FixationCrossStimulus(FullFieldVisualStimulus):
    """ Draws a simple cross in the center of the visual field

    """

    def __init__(
        self,
        cross_color=(255, 0, 0),
        position=(0.5, 0.5),
        arm_len=0.05,
        arm_width=4,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.cross_color = cross_color
        self.arm_len = arm_len
        self.arm_width = arm_width
        self.position = position
        self.name = "fixation_cross"

    def paint(self, p, w, h):
        super().paint(p, w, h)
        pen = QPen(QColor(*self.cross_color))
        pen.setWidth(self.arm_width)
        p.setPen(pen)
        #    p.setBrush(QBrush(QColor(0, 0, 0, 255)))
        l = w * self.arm_len
        w_p = w * self.position[0]
        h_p = h * self.position[1]
        p.drawLine(w_p - l, h_p, w_p + l, h_p)
        p.drawLine(w_p, h_p - l, w_p, h_p + l)
