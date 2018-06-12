from itertools import product

import numpy as np
import pims
import qimage2ndarray
from PyQt5.QtCore import QPoint, QRect, QPointF
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtGui import QTransform, QPolygon, QRegion
from stytra.stimulation import Stimulus, DynamicStimulus
from stytra.stimulation.backgrounds import existing_file_background


# TODO right now Stimulus is not parameterized via HasPyQtGraphParams


class VisualStimulus(Stimulus):
    """Stimulus class to paint programmatically on a canvas.
    For this subclass of Stimulus, their core function (paint()) is
    not called by the ProtocolRunner, but directly from the
    StimulusDisplayWindow. Since a StimulusDisplayWindow is directly linked to
    a ProtocolRunner, at every time the paint() method that is called
    is the one from the correct current stimulus.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, *args, clip_rect=None, **kwargs):
        """
        :param clip_rect: mask for clipping the stimulus ((x, y, w, h) tuple);
        """
        super().__init__(*args, **kwargs)
        self.clip_rect = clip_rect

    def paint(self, p, w, h):
        """Paint function. Called by the StimulusDisplayWindow update method.

        Parameters
        ----------
        p :
            QPainter object for drawing
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
        if self.clip_rect is not None:
            if isinstance(self.clip_rect[0], tuple):
                points = [QPoint(int(w*x), int(h*y))
                          for (x, y) in self.clip_rect]
                p.setClipRegion(QRegion(QPolygon(points)))
            else:
                p.setClipRect(self.clip_rect[0] * w, self.clip_rect[1] * h,
                              self.clip_rect[2] * w, self.clip_rect[3] * h)


class VisualStimulusCombiner(VisualStimulus):
    """Stimulus to combine multiple paint stimuli on the same canvas.
    Their respective domains can be defined via their clipping boxes.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, stim_list):
        self.stimuli = stim_list
        self.duration = max([s.duration for s in stim_list])
        self.name = '+'.join([s.name for s in stim_list])

    def start(self):
        """ """
        [s.start() for s in self.stimuli]

    def update(self):
        """ """
        super().update()
        for s in self.stimuli:
            s._elapsed = self._elapsed
            s.update()

    def get_state(self):
        """ """
        return {s.name: s.get_state() for s in self.stimuli}

    def initialise_external(self, experiment):
        """

        Parameters
        ----------
        experiment :
            

        Returns
        -------

        """
        [s.initialise_external(experiment) for s in self.stimuli]

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        [s.paint(p, w, h) for s in self.stimuli]


class FullFieldVisualStimulus(VisualStimulus):
    """Class for painting a full field flash of a specific color."""

    def __init__(self, *args, color=(255, 0, 0), **kwargs):
        """
        :param color: color of the full field flash (int tuple)
        """
        super().__init__(*args, **kwargs)
        self.color = color
        self.name = 'flash'

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))  # Use chosen color
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))  # draw full field rectangle


class DynamicFullFieldStimulus(FullFieldVisualStimulus, DynamicStimulus):
    """Paints a full field flash of a specific color, where
    luminance is dynamically changed. (Could be easily change to change color
    as well).

    ..deprecate in favour of using InterpolatedStimulus

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, *args, lum_df=None, color_0=(0, 0, 0), **kwargs):
        super().__init__(*args, dynamic_parameters=['lum', ],
                         **kwargs)
        self.color = color_0
        self.lum_df = lum_df
        self.name = 'moving seamless'
        self.duration = float(lum_df.t.iat[-1])

    def update(self):
        """ """
        super().update()
        lum = np.interp(self._elapsed, self.lum_df.t, self.lum_df['lum'])
        print(lum)
        setattr(self, 'color', (lum, )*3)


class Pause(FullFieldVisualStimulus):
    """Class for painting full field black stimuli"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'pause'


class VideoStimulus(VisualStimulus, DynamicStimulus):
    """Displays videos using PIMS, at aspecified framerate"""
    def __init__(self, *args, video_path, framerate=None, duration=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.name = 'video'

        self.dynamic_parameters.append('i_frame')
        self.i_frame = 0
        self.video_path = video_path

        self._current_frame = None
        self._last_frame_display_time = 0
        self._video_seq = None

        self.framerate = framerate
        self.duration = duration

    def initialise_external(self, *args, **kwargs):
        """

        Parameters
        ----------
        *args :
            
        **kwargs :
            

        Returns
        -------

        """
        super().initialise_external(*args, **kwargs)
        self._video_seq = pims.Video(self._experiment.asset_dir +
                                     '/' + self.video_path)

        self._current_frame = self._video_seq.get_frame(self.i_frame)
        try:
            metadata = self._video_seq.get_metadata()

            if self.framerate is None:
                self.framerate = metadata['fps']
            if self.duration is None:
                self.duration = metadata['duration']

        except AttributeError:
            if self.framerate is None:
                self.framerate = self._video_seq.frame_rate

            if self.duration is None:
                self.duration = self._video_seq.duration

    def update(self):
        """ """
        super().update()
        # if the video restarted, it means the last display time
        # is incorrect, it has to be reset
        if self._elapsed < self._last_frame_display_time:
            self._last_frame_display_time = 0
        if self._elapsed >= self._last_frame_display_time+1/self.framerate:
            self.i_frame = int(round(self._elapsed*self.framerate))
            next_frame = self._video_seq.get_frame(self.i_frame)
            if next_frame is not None:
                self._current_frame = next_frame
                self._last_frame_display_time = self._elapsed

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        display_centre = (w / 2, h / 2)
        img = qimage2ndarray.array2qimage(self._current_frame)
        p.drawImage(QPoint(display_centre[0] - self._current_frame.shape[1] // 2,
                           display_centre[1] - self._current_frame.shape[0] // 2),
                    img)


class BackgroundStimulus(VisualStimulus, DynamicStimulus):
    """Stimulus with a defined position and orientation to the fish"""
    def __init__(self, *args, **kwargs):
        """
        :param background: background image
        """
        self.x = 0
        self.y = 0
        self.theta = 0
        super().__init__(*args,
                         dynamic_parameters=["x", "y", "theta"],
                         **kwargs)

    def get_unit_dims(self, w, h):
        """

        Parameters
        ----------
        w :
            
        h :
            

        Returns
        -------

        """
        return w, h

    def get_rot_transform(self, w, h):
        """

        Parameters
        ----------
        w :
            
        h :
            

        Returns
        -------

        """
        xc = -w / 2
        yc = -h / 2
        return QTransform().translate(-xc, -yc).rotate(
            self.theta*180/np.pi).translate(xc, yc)

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        if self._experiment.calibrator is not None:
            mm_px = self._experiment.calibrator.params['mm_px']
        else:
            mm_px = 1

        # draw the black background
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        self.clip(p, w, h)

        # find the centres of the display and image
        display_centre = (w/2, h/2)
        imw, imh = self.get_unit_dims(w, h)

        image_centre = (imw / 2, imh / 2)

        cx = self.x/mm_px - np.floor(
             self.x/mm_px / imw) * imw
        cy = self.y/mm_px - np.floor(
            (self.y/mm_px) / imh) * imh

        dx = display_centre[0] - image_centre[0] + cx
        dy = display_centre[1] - image_centre[1] - cy

        # rotate the coordinate transform around the position of the fish
        p.setTransform(self.get_rot_transform(w, h))

        nw = int(np.ceil(w/(imw*2)))
        nh = int(np.ceil(h/(imh*2)))
        for idx, idy in product(range(-nw-1, nw+1), range(-nh-1, nh+1)):
            self.draw_block(p, QPointF(idx*imw+dx, idy*imh+dy), w, h)

    def draw_block(self, p, point, w, h):
        """

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


class MovingConstantVel(BackgroundStimulus):
    def __init__(self, *args, vel_x=0, vel_y=0, **kwargs):
        """

        Parameters
        ----------
        args
        vel_x
        vel_y
        kwargs
        """

        super().__init__(*args, **kwargs)
        self.vel_x = vel_x
        self.vel_y = vel_y
        self._past_t = 0

    def update(self):
        """ """
        super().update()
        dt = (self._elapsed - self._past_t)
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        self._past_t = self._elapsed



class SeamlessImageStimulus(BackgroundStimulus):
    """Class for moving an image."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qbackground = None

    def initialise_external(self, experiment):
        """

        Parameters
        ----------
        experiment :
            

        Returns
        -------

        """
        super().initialise_external(experiment)

        # Get background image from folder:
        self._qbackground = qimage2ndarray.array2qimage(
            existing_file_background(self._experiment.asset_dir + '/' +
                                     self.background))

    def get_unit_dims(self, w, h):
        """Update dimensions of the current background image.

        Parameters
        ----------
        w :
            
        h :
            

        Returns
        -------

        """
        w, h = self._qbackground.width(),  self._qbackground.height()
        return w, h

    def draw_block(self, p, point, w, h):
        """

        Parameters
        ----------
        p :
            
        point :
            
        w :
            
        h :
            

        Returns
        -------

        """
        p.drawImage(point, self._qbackground)


class SeamlessGratingStimulus(BackgroundStimulus):
    """Class for moving a grating pattern."""
    def __init__(self, *args, grating_angle=0, grating_period=10,
                 color=(255, 255, 255), **kwargs):
        """
        :param grating_angle: fixed angle for the stripes
        :param grating_period: spatial period of the gratings (unit?)
        :param grating_color: color for the non-black stripes (int tuple)
        """
        super().__init__(*args, **kwargs)
        self.theta = grating_angle
        self.grating_period = grating_period
        self.color = color
        self.name = 'moving_gratings'

    def get_unit_dims(self, w, h):
        """

        Parameters
        ----------
        w :
            
        h :
            

        Returns
        -------

        """
        return self.grating_period / max(self._experiment.calibrator.params['mm_px'], 0.0001), max(w, h)

    def draw_block(self, p, point, w, h):
        """Draws one bar of the grating, the rest are repeated by tiling

        Parameters
        ----------
        p :
            
        point :
            
        w :
            
        h :
            

        Returns
        -------

        """
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(*self.color)))
        p.drawRect(point.x(), point.y(),
                   int(self.grating_period / (2 * max(self._experiment.calibrator.params['mm_px'], 0.0001))),
                   w)


class SeamlessWindmillStimulus(BackgroundStimulus):
    """Class for drawing a rotating windmill."""

    def __init__(self, *args, color=(255, 255, 255), n_arms=8, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.n_arms = n_arms
        self.name = 'windmill'

    def draw_block(self, p, point, w, h):
        """

        Parameters
        ----------
        p :
            
        point :
            
        w :
            
        h :
            

        Returns
        -------

        """
        # Painting settings:
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(*self.color)))

        # To draw a windmill, a set of consecutive triangles will be painted:
        mid_x = int(w / 2)  # calculate image center
        mid_y = int(h / 2)

        # calculate angles for each triangle:
        angles = np.arange(0, np.pi * 2, (np.pi * 2) / self.n_arms)
        angles += np.pi/2 + np.pi/(2 * self.n_arms)
        # angular width of the white arms, by default equal to dark ones
        size = np.pi / self.n_arms
        # radius of triangles (much larger than frame)
        rad = (w ** 2 + h ** 2) ** (1 / 2)

        # loop over angles and draw consecutive triangles
        for deg in np.array(angles):
            polyg_points = [QPoint(mid_x, mid_y),
                            QPoint(int(mid_x + rad * np.cos(deg)),
                                   int(mid_y + rad * np.sin(deg))),
                            QPoint(int(mid_x + rad * np.cos(deg + size)),
                                   int(mid_y + rad * np.sin(deg + size)))]
            polygon = QPolygon(polyg_points)
            p.drawPolygon(polygon)


# Stimuli which need to be implemented

class RandomDotKinematogram(VisualStimulus):
    """ """
    def __init__(self, *args, dot_density, coherence, velocity, direction, **kwargs):
        super().__init__(*args, **kwargs)
        self.dot_density = dot_density
        self.coherence = coherence
        self.velocity = velocity
        self.direction = direction
        self.dots = None

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        # TODO implement dot painting and update
        pass


class SparseNoiseStimulus(DynamicStimulus, VisualStimulus):
    """ """
    def __init__(self, *args, spot_radius=5, average_distance=20,
                 n_spots=10, **kwargs):
        super().__init__()
        self.dynamic_parameters = ['spot_positions']
        self.spot_radius = spot_radius
        self.average_distance = 20
        self.spot_positions = np.array((n_spots, 2))

    def paint(self, p, w, h):
        """

        Parameters
        ----------
        p :
            
        w :
            
        h :
            

        Returns
        -------

        """
        pass


class CircleStimulus(VisualStimulus, DynamicStimulus):
    """ A circle stimulus, which in combination with interpolation
    can be used to make looming stimuli"""
    def __init__(self, origin=(0.5, 0.5), radius=0,
                 background_color=(0, 0, 0),
                 circle_color=(255, 255, 255)):
        super().__init__(dynamic_parameters=["radius"])
        self.origin = origin
        self.radius = radius
        self.background_color = background_color
        self.circle_color = circle_color

    def paint(self, p, w, h):
        super().paint(p, w, h)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.background_color)))  # Use chosen color
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        p.setBrush(QBrush(QColor(*self.circle_color)))
        p.drawEllipse(QPointF(w*self.origin[1], h*self.origin[0]), self.radius, self.radius)
