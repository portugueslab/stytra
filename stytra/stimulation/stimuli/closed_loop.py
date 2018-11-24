from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor

import numpy as np

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    CircleStimulus,
    PositionStimulus,
    InterpolatedStimulus,
)


class ClosedLoop1D(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """
    Vigor-based closed loop stimulus. Velocity is assumend to be calculated
    with the

    The parameters can change in time if the df_param is supplied which
    specifies their values in time.

    Parameters
    ----------
    base_vel:
        the velocity of the background when the stimulus is not moving
    gain:
        the closed-loop gain, a gain of 1 approximates
        the freely-swimming behavior
    lag:
        how much extra delay is provided in the closed loop
    shunting: bool
        if true, when the fish stops swimming its infulence on the
        background motion stops, immediately independent of lag
    swimming_threshold: float
        the velocity at which the fish is considered to be performing
        a bout
    fixed_vel: float
        if not None, fixed velocity for the stimulus when fish swims
    """

    def __init__(
        self,
        *args,
        base_vel=10,
        gain=1,
        lag=0,
        shunting=False,
        swimming_threshold=0.2 * -30,
        max_vel=40,
        fixed_vel=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "closed loop 1D"
        self.fish_vel = 0
        self.dynamic_parameters = ["vel", "base_vel",
                                   "gain", "lag", "fish_swimming"]
        self.base_vel = base_vel
        self.fish_vel = 0
        self.vel = base_vel
        self.lag = lag
        self.gain = gain
        self.swimming_threshold = swimming_threshold
        self.fish_swimming = False
        self.shunting = shunting
        self.shunted = False
        self.fixed_vel = fixed_vel  # fixed forward velocity
        self.max_vel = max_vel

        self.bout_start = None
        self.bout_stop = None

        self._past_t = 0

    def update(self):
        """
        Here we use fish velocity to change velocity of gratings.
        """
        super().update()

        self.fish_vel = self._experiment.estimator.get_velocity(lag=self.lag)

        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if (
            self.shunting
            and self.fish_swimming
            and self.fish_vel > self.swimming_threshold
        ):
            self.shunted = True

        # If estimated velocity greater than threshold
        # the fish is performing a bout:
        if self.fish_vel < self.swimming_threshold:  # if bouting:
            self.fish_swimming = True

            if self.bout_start is None:
                self.bout_start = self._elapsed
            self.bout_stop = None
        else:  # if not bouting:
            self.bout_start = None
            if self.bout_stop is None:
                self.bout_stop = self._elapsed

            self.fish_swimming = False

        if self.fixed_vel is None:
            self.vel = int(not self.shunted) * (
                self.base_vel - self.fish_vel * self.gain * int(self.fish_swimming)
            )
        else:
            if self.fish_swimming and not self.base_vel == 0:
                self.vel = self.fixed_vel
            else:
                self.vel = self.base_vel


        self.x += self._dt * self.vel


class CalibratingClosedLoop1D(BackgroundStimulus, InterpolatedStimulus,
                              DynamicStimulus):
    """
    Vigor-based closed loop stimulus. Velocity is assumend to be calculated
    with the

    The parameters can change in time if the df_param is supplied which
    specifies their values in time.

    Parameters
    ----------
    base_vel:
        the velocity of the background when the stimulus is not moving
    swimming_threshold: float
        the velocity at which the fish is considered to be performing
        a bout
    """

    def __init__(
        self,
        *args,
        base_vel=10,
        swimming_threshold=-5,
        max_vel=40,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "closed loop 1D"
        self.fish_vel = 0
        self.dynamic_parameters = ["vel", "base_vel", "fish_swimming",
                                   ]
        self.base_vel = base_vel
        self.fish_vel = 0
        self.vel = base_vel
        self.target_vel = -15  # target velocity for the calibration

        self.swimming_threshold = swimming_threshold
        self.fish_swimming = False
        self.max_vel = max_vel

        self.bout_start = None
        self.bout_stop = None
        self.bout_counter = None
        self.bout_peak_vel = 0
        self.bout_vel_list = []

        self._past_t = 0

    def update(self):
        """
        Here we use fish velocity to change velocity of gratings.
        """
        super().update()

        self.fish_vel = self._experiment.estimator.get_velocity()

        # if self.base_vel == 0:
        #     self.fish_swimming = False  # cut reafference when gratings are
        #  not moving

        # If estimated velocity greater than threshold
        # the fish is performing a bout:

        if self.fish_vel < self.swimming_threshold:  # if bouting:
            self.fish_swimming = True

            # If we are at the beginning of a bout:
            if self.bout_start is None:
                self.bout_stop = None
                self.bout_start = self._elapsed
                self.bout_counter += 1

            # Update peak velocity for this bout:
            self.bout_peak_vel = max(self.bout_peak_vel, self.fish_vel)

        else:  # if not bouting:
            if self.bout_stop is None:
                self.bout_start = None
                self.bout_stop = self._elapsed

                # Update list with peak velocities and reset current peak vel:
                self.bout_vel_list.append(self.bout_peak_vel)
                self.bout_peak_vel = 0

                # After some number of bouts, update estimator gain:

                if len(self.bout_vel_list) > 10:
                    median_peak_vel = np.median(self.bout_vel_list)
                    gain = self.target_vel / median_peak_vel
                    self._experiment.estimator.base_gain = gain

            self.fish_swimming = False

        self.vel = self.base_vel - self.fish_vel * int(self.fish_swimming)

        self.vel = np.min(self.vel, self.max_vel)  # set maximum vel possible

        self.x += self._dt * self.vel


class PerpendicularMotion(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """ A stimulus which is always kept perpendicular to the fish

    """

    def update(self):
        x, y, theta = self._experiment.estimator.get_position()
        if np.isfinite(theta):
            self.theta = theta
        super().update()


class FishTrackingStimulus(PositionStimulus):
    def update(self):
        y, x, theta = self._experiment.estimator.get_position()
        if np.isfinite(theta):
            self.x = x
            self.y = y
            self.theta = theta
        super().update()


class CenteringWrapper(PositionStimulus):
    """ A meta-stimulus which turns on centering if the fish
    veers too much towrds the edge

    """

    def __init__(self, stimulus, centering, margin=200, **kwargs):
        super().__init__(**kwargs)
        self.margin = margin ** 2
        self.stimulus = stimulus
        self.active = self.stimulus
        self.centering = centering
        self.xc = 320
        self.yc = 240
        self.duration = self.stimulus.duration

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.stimulus.initialise_external(experiment)
        self.centering.initialise_external(experiment)

    def update(self):
        y, x, theta = self._experiment.estimator.get_position()
        if x < 0 or ((x - self.xc) ** 2 + (y - self.yc) ** 2) > self.margin:
            self.active = self.centering
        else:
            self.active = self.stimulus
        self.active._elapsed = self._elapsed
        self.active.update()

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        self.active.paint(p, w, h)


class TrackingStimulus(CircleStimulus):
    def update(self):
        self.x, self.y, _ = self._experiment.estimator.get_position()
        super().update()
