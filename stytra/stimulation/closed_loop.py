import numpy as np
from stytra.stimulation import DynamicStimulus
from stytra.stimulation.visual import BackgroundStimulus, SeamlessImageStimulus, CircleStimulus


class ClosedLoop1D(BackgroundStimulus, DynamicStimulus):
    """ """
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
        """ """
        super().update()
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


class VRMotionStimulus(SeamlessImageStimulus,
                       DynamicStimulus):
    """ """

    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion
        self.dynamic_parameters = ['x', 'y', 'theta', 'dv']
        self._bg_x = 0
        self._bg_y = 0
        self.dv = 0
        self._past_t = 0

    def update(self):
        """ """
        super().update()
        dt = self._elapsed - self._past_t
        vel_x = np.interp(self._elapsed, self.motion.t, self.motion.vel_x)
        vel_y = np.interp(self._elapsed, self.motion.t, self.motion.vel_y)
        self._bg_x += vel_x * dt
        self._bg_y += vel_y * dt

        fish_coordinates = self._experiment.position_estimator.get_displacements()

        self.x = self._bg_x + fish_coordinates[1]  # A right angle turn between the cooridnate systems
        self.y = self._bg_y - fish_coordinates[0]
        # on the upper right
        self.theta = fish_coordinates[2]
        self._past_t = self._elapsed


class ObjectTrackingSitmulus(CircleStimulus):
    def update(self):
        self.x, self.y = self._experiment.position_estimator.get_position()
        super().update()
