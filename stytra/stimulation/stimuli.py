import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QTransform, QPolygon, QRegion
import qimage2ndarray
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor
from PyQt5.QtCore import QPoint, QRect, QRectF, QPointF
import pims
from stytra.stimulation.backgrounds import existing_file_background



from itertools import product


class Stimulus:
    """ General class for a stimulus. Each stimulus can act one through the
     start() function. It is called when the ProtocolRunner sets it as the
     new stimulus. It can for example trigger external events
     (e.g., activate a Pyboard).

    Different stimuli categories are implemented subclassing this class, e.g.:
     - visual stimuli (children of PainterStimulus subclass);
     ...

    """
    def __init__(self, duration=0.0):
        """ Make a stimulus, with the basic properties common to all stimuli.
        Values not to be logged start with _

        :param duration: duration of the stimulus (s)
        """

        self.duration = duration

        self._started = None
        self._elapsed = 0.0  # time from the beginning of the stimulus
        self.name = ''
        self._experiment = None

    def get_state(self):
        """ Returns a dictionary with stimulus features for the log.
        Ignores the properties which are private (start with _)
        """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != '_':
                state_dict[key] = value
        return state_dict

    def update(self):
        pass

    def start(self):
        pass

    def initialise_external(self, experiment):
        """ Make a reference to the Experiment class inside the Stimulus.
        This is required to access from inside the Stimulus class to the
        Calibrator, the Pyboard, the asset directories with movies or the motor
        estimator for virtual reality.

        :param experiment: the experiment object to which link the stimulus
        :return: None
        """
        self._experiment = experiment


class DynamicStimulus(Stimulus):
    """ Stimuli where parameters change during stimulation on a frame-by-frame
    base, implements the recording changing parameters.
    """
    def __init__(self, *args, dynamic_parameters=None, **kwargs):
        """
        :param dynamic_parameters: A list of all parameters that are to be
                                   recorded frame by frame;
        """
        super().__init__(*args, **kwargs)
        if dynamic_parameters is None:
            self.dynamic_parameters = []
        else:
            self.dynamic_parameters = dynamic_parameters

    def get_dynamic_state(self):
        """ Return the state of constantly varying parameters.
        """
        return tuple(getattr(self, param, 0)
                     for param in self.dynamic_parameters)


class PainterStimulus(Stimulus):
    """ Stimulus class where image is programmatically drawn on a canvas.
    Their paint() function is called by the StimulusDisplayWindow
    paintEvent(), and ensure that at every time the function used
    to paint the new frame is the one from the current stimulus.
    """
    def __init__(self, *args, clip_rect=None, **kwargs):
        """
        :param clip_rect: mask for clipping the stimulus ((x, y, w, h) tuple);
        """
        super().__init__(*args, **kwargs)
        self.clip_rect = clip_rect

    def paint(self, p, w, h):
        """ Paint function (redefined in children classes)
        :param p: QPainter object for drawing
        :param w: width of the display window
        :param h: height of the display window
        """
        pass

    def clip(self, p, w, h):
        """ Clip image before painting
        :param p: QPainter object used for painting
        :param w: image width
        :param h: image height
        """
        if self.clip_rect is not None:
            if isinstance(self.clip_rect[0], tuple):
                points = [QPoint(int(w*x), int(h*y)) for (x, y) in self.clip_rect]
                p.setClipRegion(QRegion(QPolygon(points)))
            else:
                p.setClipRect(self.clip_rect[0] * w, self.clip_rect[1] * h,
                              self.clip_rect[2] * w, self.clip_rect[3] * h)


class BackgroundStimulus(Stimulus):
    """ Stimulus consisting in a full field image that can be dragged around.
    """
    def __init__(self, *args, background=None, **kwargs):
        """
        :param background: background image
        """
        super().__init__(*args, **kwargs)
        self.x = 0
        self.y = 0
        self.theta = 0
        self.background = background


class MovingStimulus(DynamicStimulus, BackgroundStimulus):
    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, dynamic_parameters=['x', 'y', 'theta'],
                         **kwargs)
        self.motion = motion
        self.name = 'moving seamless'
        self.duration = float(motion.t.iat[-1])

    def update(self):
        for attr in ['x', 'y', 'theta']:
            try:
                setattr(self, attr, np.interp(self._elapsed, self.motion.t, self.motion[attr]))

            except (AttributeError, KeyError):
                pass


class MovingConstantVel(MovingStimulus):
    def __init__(self, *args, x_vel=0, y_vel=0, **kwargs):
        """
        :param x_vel: x drift velocity (mm/s)
        :param y_vel: x drift velocity (mm/s)
        :param mm_px: mm per pixel
        :param monitor_rate: monitor rate (in Hz)
        """
        super().__init__(*args, **kwargs)
        self.x_vel = x_vel
        self.y_vel = y_vel
        self._past_t = 0

    def update(self):
        dt = (self._elapsed - self._past_t)
        self.x += self.x_vel*dt
        self.y += self.y_vel*dt
        self._past_t = self._elapsed


class MovingDynamicVel(MovingStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._past_t = 0

    def update(self):
        dt = self._elapsed - self._past_t

        for attr in ['x', 'y', 'theta']:
            try:
                setattr(self, attr,
                        getattr(self, attr) +
                        dt*np.interp(self._elapsed, self.motion.t, self.motion['vel_'+attr]))

            except (AttributeError, KeyError):
                pass

        self._past_t = self._elapsed



class FullFieldPainterStimulus(PainterStimulus):
    """ Class for painting a full field flash of a specific color.
    """

    def __init__(self, *args, color=(255, 0, 0), **kwargs):
        """
        :param color: color of the full field flash (int tuple)
        """
        super().__init__(*args, **kwargs)
        self.color = color
        self.name = 'flash'

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))  # Use chosen color
        self.clip(p, w, h)
        p.drawRect(QRect(-1, -1, w + 2, h + 2))  # draw full field rectangle


class DynamicFullFieldStimulus(FullFieldPainterStimulus, DynamicStimulus):
    """ Class for painting a full field flash of a specific color, where
    luminance is dynamically changed. (Could be easily change to change color
    as well).
    """
    def __init__(self, *args, lum_df=None, color_0=(0, 0, 0), **kwargs):
        super().__init__(*args, dynamic_parameters=['lum', ],
                         **kwargs)
        self.color = color_0
        self.lum_df = lum_df
        self.name = 'moving seamless'
        self.duration = float(lum_df.t.iat[-1])

    def update(self):
        lum = np.interp(self._elapsed, self.lum_df.t, self.lum_df['lum'])
        print(lum)
        setattr(self, 'color', (lum, )*3)


class Pause(FullFieldPainterStimulus):
    """ Class for painting full field black stimuli
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'pause'


# TODO why not use MovingStimulus?
class MovingSeamlessStimulus(PainterStimulus,
                             DynamicStimulus,
                             BackgroundStimulus):
    """ Class for moving a stimulus image or pattern, thought for a VR setup.
    """
    def get_unit_dims(self, w, h):
        return w, h

    def get_rot_transform(self, w, h):
        xc = -w / 2
        yc = -h / 2
        return QTransform().translate(-xc, -yc).rotate(
            self.theta*180/np.pi).translate(xc, yc)

    def paint(self, p, w, h):
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
        pass


class SeamlessImageStimulus(MovingSeamlessStimulus):
    """ Class for moving an image.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._qbackground = None

    def initialise_external(self, experiment):
        super().initialise_external(experiment)

        # Get background image from folder:
        self._qbackground = qimage2ndarray.array2qimage(
            existing_file_background(self._experiment.asset_dir + '/' +
                                     self.background))

    def get_unit_dims(self, w, h):
        """ Update dimensions of the current background image.
        """
        w, h = self._qbackground.width(),  self._qbackground.height()
        return w, h

    def draw_block(self, p, point, w, h):
        p.drawImage(point, self._qbackground)


class SeamlessGratingStimulus(MovingSeamlessStimulus, MovingStimulus):
    """ Class for moving a grating pattern.
    """
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
        """
        return self.grating_period / max(self._experiment.calibrator.params['mm_px'], 0.0001), max(w, h)

    def draw_block(self, p, point, w, h):
        """ Function for drawing the gratings programmatically.
        """
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(*self.color)))
        p.drawRect(point.x(), point.y(),
                   int(self.grating_period / (2 * max(self._experiment.calibrator.params['mm_px'], 0.0001))),
                   w)


class SparseNoiseStimulus(DynamicStimulus, PainterStimulus):
    def __init__(self, *args, spot_radius=5, average_distance=20,
                 n_spots=10, **kwargs):
        super().__init__()
        self.dynamic_parameters = ['spot_positions']
        self.spot_radius = spot_radius
        self.average_distance = 20
        self.spot_positions = np.array((n_spots, 2))

    def paint(self, p, w, h):
        pass


class VideoStimulus(PainterStimulus, DynamicStimulus):
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
        display_centre = (w / 2, h / 2)
        img = qimage2ndarray.array2qimage(self._current_frame)
        p.drawImage(QPoint(display_centre[0] - self._current_frame.shape[1] // 2,
                           display_centre[1] - self._current_frame.shape[0] // 2),
                    img)


class ClosedLoop1D(BackgroundStimulus, DynamicStimulus):
    def __init__(self, *args, default_velocity=10, gain=1,
                 shunting=False,
                 base_gain=5,
                 swimming_threshold=0.2,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.name = 'closed loop 1D'
        self.fish_velocity = 0
        self.dynamic_parameters.append('vel')
        self.dynamic_parameters.append('y')
        self.dynamic_parameters.append('fish_velocity')
        self.base_vel = default_velocity
        self.fish_velocity = 0
        self.vel = 0
        self.gain = gain
        self.base_gain = base_gain
        self.swimming_threshold = swimming_threshold
        self.fish_swimming = False
        self.shunting = shunting
        self.shunted = False

        self._past_x = self.x
        self._past_y = self.y
        self._past_theta = self.theta
        self._past_t = 0

    def update(self):
        dt = (self._elapsed - self._past_t)
        self.fish_velocity = self._experiment.fish_motion_estimator.get_velocity()
        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if self.shunting and self.fish_swimming and self.fish_velocity < self.swimming_threshold:
            self.shunted = True

        if self.fish_velocity > self.swimming_threshold:
            self.fish_swimming = True

        self.vel = int(not self.shunted) * (self.base_vel - \
                   self.fish_velocity * self.gain * self.base_gain * int(self.fish_swimming))

        if self.vel is None or self.vel > 15:
            print('I am resetting vel to 0 because it is strange.')
            self.vel = 0

        self.y += dt * self.vel
        # TODO implement lag
        self._past_t = self._elapsed
        for attr in ['x', 'y', 'theta']:
            try:
                setattr(self, 'past_'+attr, getattr(self, attr))
            except (AttributeError, KeyError):
                pass


class SeamlessWindmillStimulus(MovingSeamlessStimulus, MovingStimulus):
    """ Class for drawing a rotating windmill.
    """

    def __init__(self, *args, color=(255, 255, 255), n_arms=8, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.n_arms = n_arms
        self.name = 'windmill'

    def draw_block(self, p, point, w, h):
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
        for deg in angles:  # loop over angles and draw consecutive rectangles
            polyg_points = [QPoint(mid_x, mid_y),
                            QPoint(int(mid_x + rad * np.cos(deg)),
                                   int(mid_y + rad * np.sin(deg))),
                            QPoint(int(mid_x + rad * np.cos(deg + size)),
                                   int(mid_y + rad * np.sin(deg + size)))]
            polygon = QPolygon(polyg_points)
            p.drawPolygon(polygon)


class VRMotionStimulus(SeamlessImageStimulus,
                       DynamicStimulus):

    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion
        self.dynamic_parameters = ['x', 'y', 'theta', 'dv']
        self._bg_x = 0
        self._bg_y = 0
        self.dv = 0
        self._past_t = 0

    def update(self):
        dt = self._elapsed - self._past_t
        vel_x = np.interp(self._elapsed, self.motion.t, self.motion.vel_x)
        vel_y = np.interp(self._elapsed, self.motion.t, self.motion.vel_y)
        self._bg_x += vel_x * dt
        self._bg_y += vel_y * dt

        fish_coordinates = self._experiment.position_estimator.get_displacements()

        self.x = self._bg_x + fish_coordinates[1] # A right angle turn between the cooridnate systems
        self.y = self._bg_y - fish_coordinates[0]
        # on the upper right
        self.theta = fish_coordinates[2]
        self._past_t = self._elapsed


class RandomDotKinematogram(PainterStimulus):
    def __init__(self, *args, dot_density, coherence, velocity, direction, **kwargs):
        super().__init__(*args, **kwargs)
        self.dot_density = dot_density
        self.coherence = coherence
        self.velocity = velocity
        self.direction = direction
        self.dots = None

    def paint(self, p, w, h):
        # TODO implement dot painting and update
        pass


class ShockStimulus(Stimulus):
    def __init__(self, burst_freq=100, pulse_amp=3., pulse_n=5,
                 pulse_dur_ms=2, pyboard=None, **kwargs):
        """
        Burst of electric shocks through pyboard (Anki's code)
        :param burst_freq: burst frequency (Hz)
        :param pulse_amp: pulse amplitude (mA)
        :param pulse_n: number of pulses
        :param pulse_dur_ms: pulses duration (ms)
        :param pyboard: PyboardConnection object
        """
        try:
            from stytra.hardware.serial import PyboardConnection
        except ImportError:
            print('Serial pyboard connection not installed')

        super().__init__(**kwargs)
        self.name = 'shock'
        # assert isinstance(pyboard, PyboardConnection)
        self._pyb = pyboard
        self.burst_freq = burst_freq
        self.pulse_dur_ms = pulse_dur_ms
        self.pulse_n = pulse_n
        self.pulse_amp_mA = pulse_amp

        # Pause between shocks in the burst in ms:
        self.pause = 1000/burst_freq - pulse_dur_ms

        amp_dac = str(int(255*pulse_amp/3.5))
        pulse_dur_str = str(pulse_dur_ms).zfill(3)
        self.mex = str('shock' + amp_dac + pulse_dur_str)

    def start(self):
        for i in range(self.pulse_n):
            self._pyb.write(self.mex)
            print(self.mex)
        self.elapsed = 1