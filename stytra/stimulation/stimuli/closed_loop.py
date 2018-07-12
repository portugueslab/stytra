import numpy as np

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    SeamlessImageStimulus,
    CircleStimulus,
    MovingGratingStimulus,
    InterpolatedStimulus
)


class ClosedLoop1D(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """ """

    def __init__(
        self,
        *args,
        default_velocity=10,
        gain=1,
        shunting=False,
        base_gain=-30,
        swimming_threshold=0.2,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "closed loop 1D"
        self.fish_velocity = 0
        self.dynamic_parameters = ["vel", "fish_velocity", "gain"]
        self.base_vel = default_velocity
        self.fish_velocity = 0
        self.vel = 0
        self.gain = gain
        self.base_gain = base_gain
        self.swimming_threshold = swimming_threshold
        self.fish_swimming = False
        self.shunting = shunting
        self.shunted = False

        self.bout_start = None
        self.bout_stop = None

        self._past_t = 0

    def update(self):
        """
        Here we use fish velocity to change velocity of gratings.
        """
        dt = super().update()

        self.fish_velocity = self._experiment.estimator.get_velocity(lag=0)

        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if self.shunting and self.fish_swimming and self.fish_velocity < self.swimming_threshold:
            self.shunted = True

        # If estimated velocity greater than threshold
        # the fish is performing a bout
        if self.fish_velocity > self.swimming_threshold:
            self.fish_swimming = True

            if self.bout_start is None:
                self.bout_start = self._elapsed
            self.bout_stop = None
        else:
            self.bout_start = None
            if self.bout_start is None:
                self.bout_start = self._elapsed

            self.fish_swimming = False

        self.vel = int(not self.shunted) * (self.base_vel -
                   self.fish_velocity * self.gain * self.base_gain * int(self.fish_swimming))

        if self.vel is None or self.vel > 50:
            self.vel = 0

        self.x += dt * self.vel


class VRMotionStimulus(SeamlessImageStimulus, DynamicStimulus):
    """ """

    def __init__(self, *args, motion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.motion = motion
        self.dynamic_parameters = ["x", "y", "theta", "dv"]
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

        fish_coordinates = self._experiment.estimator.get_displacements()

        self.x = (
            self._bg_x + fish_coordinates[1]
        )  # A right angle turn between the cooridnate systems
        self.y = self._bg_y - fish_coordinates[0]

        # on the upper right
        self.theta = fish_coordinates[2]
        self._past_t = self._elapsed


class TrackingStimulus(CircleStimulus):

    def update(self):
        self.x, self.y, _ = self._experiment.estimator.get_position()
        super().update()
