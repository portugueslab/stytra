import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QTransform
import qimage2ndarray
from PyQt5.QtGui import QPainter, QImage, QBrush, QPen, QColor
from PyQt5.QtCore import QPoint, QRect, QRectF
import pims
from time import sleep
try:
    from stytra.hardware.serial import PyboardConnection
except ImportError:
    print('Serial pyboard connection not installed')

from itertools import product


class Stimulus:
    """ General class for a stimulus."""
    def __init__(self, duration=0.0):
        """ Make a stimulus, with the basic properties common to all stimuli
        Initial values which do not change during the stimulus
        are prefixed with _, so that they are not logged
        at every time step

        :param duration: duration of the stimulus (s)
        """
        self._started = None
        self._elapsed = 0.0
        self.duration = duration
        self.name = ''
        self._calibrator = None
        self._asset_folder = None

    def get_state(self):
        """ Returns a dictionary with stimulus features
        ignores the properties which are private (start with _)
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

    def initialise_external(self, calibrator=None,
                            asset_folder=None):
        """ Functions that initiate each stimulus,
        gets around problems with copying

        :param calibrator:
        :param asset_folder:
        :return:
        """
        self._calibrator = calibrator
        self._asset_folder = asset_folder


class DynamicStimulus(Stimulus):
    """ Stimuli where parameters change during stimulation, used
    to record form stimuli which react to the fish

    """
    def __init__(self, *args, dynamic_parameters=None, **kwargs):
        """

        :param args:
        :param dynamic_parameters: A list of all parameters that are to be recorded
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        if dynamic_parameters is None:
            self.dynamic_parameters = []
        else:
            self.dynamic_parameters = dynamic_parameters

    def get_dynamic_state(self):
        return tuple(getattr(self, param, 0)
                     for param in self.dynamic_parameters)


class PainterStimulus(Stimulus):
    def paint(self, p, w, h):
        pass


class BackgroundStimulus(Stimulus):
    def __init__(self, *args, background=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = 0
        self.y = 0
        self.theta = 0
        self._background = background


class FullFieldPainterStimulus(PainterStimulus):
    def __init__(self, *args, color=(255, 0, 0), **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.name = 'flash'

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))


class PartFieldStimulus(PainterStimulus):
    def __init__(self, *args, color=(255, 0, 0),
                 bounding_box=(0,0,1,1), **kwargs):
        super().__init__(*args, **kwargs)
        self.name = 'part_field'
        self.color = color
        self.bounding_box = bounding_box

    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(*self.color)))
        p.drawRect(QRect(
              int(self.bounding_box[0] * w),
              int(self.bounding_box[1] * h),
              int(self.bounding_box[2] * w),
              int(self.bounding_box[3] * h)
        ))


class Pause(FullFieldPainterStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=(0, 0, 0), **kwargs)
        self.name = 'pause'


class SeamlessImageStimulus(PainterStimulus,
                              DynamicStimulus,
                              BackgroundStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_unit_dims(self, w, h):
        return self._background.width(),  self._background.height()

    def rotTransform(self, w, h):
        xc = -w / 2
        yc = -h / 2
        return QTransform().translate(-xc, -yc).rotate(
            self.theta*180/np.pi).translate(xc, yc)

    def paint(self, p, w, h):
        # draw the black background
        if self._calibrator is not None:
            mm_px = self._calibrator.mm_px
        else:
            mm_px = 1

        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        # find the centres of the display and image
        display_centre = (w/2, h/2)
        imw, imh = self.get_unit_dims(w, h)

        image_centre = (imw / 2, imh / 2)

        cx = self.x - np.floor(self.x / imw) * imw
        cy = -self.y/mm_px - np.floor(
            -(self.y/mm_px) / imh) * imh

        dx = display_centre[0] - image_centre[0] + cx
        dy = display_centre[1] - image_centre[1] - cy

        # rotate the coordinate transform around the position of the fish
        p.setTransform(self.rotTransform(w, h))

        nw = int(np.ceil(w/(imw*2)))
        nh = int(np.ceil(h/(imh*2)))
        for idx, idy in product(range(-nw, nw+1), range(-nh, nh+1)):
            self.draw_block(p, QPoint(idx*imw+dx, idy*imh+dy), w, h)

    def draw_block(self, p, point, w, h):
        p.drawImage(point, self._background)


class SeamlessGratingStimulus(SeamlessImageStimulus):
    def __init__(self, *args, grating_angle=0, grating_period=10,
                 grating_color=(255, 255, 255), **kwargs):
        super().__init__(*args, **kwargs)
        self.theta = grating_angle
        self.grating_period = grating_period
        self.grating_color = grating_color

    def get_unit_dims(self, w, h):
        return self.grating_period / max(self._calibrator.mm_px, 0.0001), max(w, h)

    def draw_block(self, p, point, w, h):
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(*self.grating_color)))
        p.drawRect(point.x(), point.y(),
                   int(self.grating_period / (2 * max(self._calibrator.mm_px, 0.0001))),
                   w)


class GratingPainterStimulus(PainterStimulus, BackgroundStimulus,
                             DynamicStimulus):
    def __init__(self, *args, grating_orientation='horizontal', grating_period=10,
                 grating_color=(255, 255, 255), **kwargs):
        super().__init__(*args, **kwargs)
        self.theta = grating_orientation
        self.grating_period = grating_period
        self.grating_color = grating_color

    def paint(self, p, w, h):
        # draw the background
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))

        grating_width = self.grating_period/max(self._calibrator.mm_px, 0.0001) # in pixels
        p.setBrush(QBrush(QColor(*self.grating_color)))
        if self.grating_orientation == 'horizontal':
            n_gratings = int(np.round(w / grating_width + 2))
            start = -self.y / self._calibrator.mm_px - \
                    np.floor((-self.y / self._calibrator.mm_px) / grating_width + 1) * grating_width

            for i in range(n_gratings):
                p.drawRect(-1, int(round(start)), w+2, grating_width/2)
                start += grating_width
        else:
            n_gratings = int(np.round(h / grating_width + 2))
            start = self.x / self._calibrator.mm_px - \
                    np.floor(self.x / grating_width) * grating_width
            for i in range(n_gratings):
                p.drawRect(int(round(start)), -1, grating_width / 2, h+2)
                start += grating_width


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


class MovingStimulus(DynamicStimulus, BackgroundStimulus):
    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, dynamic_parameters=['x', 'y', 'theta'],
                         **kwargs)
        self.motion = motion
        self.name = 'moving seamless'

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


class VideoStimulus(PainterStimulus, DynamicStimulus):
    def __init__(self, *args, video_path, framerate=None, duration=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.name='video'

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
        print(self._asset_folder +
              '/' + self.video_path)
        self._video_seq = pims.Video(self._asset_folder +
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
        if self._elapsed >= self._last_frame_display_time+1/self.framerate:
            next_frame = self._video_seq.get_frame(self.i_frame)
            if next_frame is not None:
                self._current_frame = next_frame
                self._last_frame_display_time = self._elapsed
                self.i_frame += 1

    def paint(self, p, w, h):
        display_centre = (w / 2, h / 2)
        img = qimage2ndarray.array2qimage(self._current_frame)
        p.drawImage(QPoint(display_centre[0] - self._current_frame.shape[1] // 2,
                           display_centre[1] - self._current_frame.shape[0] // 2),
                    img)


class ClosedLoop1D(BackgroundStimulus, DynamicStimulus):
    def __init__(self, *args, default_velocity=10,
                 fish_motion_estimator, gain=1,
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
        self._fish_motion_estimator = fish_motion_estimator
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
        self.fish_velocity = self._fish_motion_estimator.get_velocity()
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


class ClosedLoop1D_variable_motion(ClosedLoop1D, GratingPainterStimulus):
    def __init__(self, *args, motion, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion
        self.duration = motion.t.iloc[-1]

    def update(self):
        for attr in ['base_vel', 'gain', 'lag']:
            try:
                setattr(self, attr, np.interp(self._elapsed,
                                              self.motion.t,
                                              self.motion[attr]))
            except (AttributeError, KeyError):
                pass
        super().update()


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
            #sleep(self.pause/1000)

        self.elapsed = 1


if __name__ == '__main__':
    pyb = PyboardConnection(com_port='COM3')
    stim = ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
                         pulse_n=1, pulse_dur_ms=5)
    stim.start()
    del pyb

