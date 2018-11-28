from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor

import numpy as np
from random import choices

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    CircleStimulus,
    PositionStimulus,
    InterpolatedStimulus,
)


class Basic_CL_1D(BackgroundStimulus, InterpolatedStimulus, DynamicStimulus):
    """
        Vigor-based closed loop stimulus.

        The parameters can change in time if the df_param is supplied which
        specifies their values in time.

        Parameters
        ----------
        base_vel:
            the velocity of the background when the stimulus is not moving
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
            swimming_threshold=-2,
            max_fish_vel=40,
            **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "general_cl1D"
        self.dynamic_parameters = ["vel", "base_vel", "fish_swimming"]
        self.base_vel = base_vel  # base grating velocity
        self.vel = base_vel  # final grating velocity

        self.swimming_threshold = swimming_threshold
        self.max_fish_vel = max_fish_vel

        self.fish_vel = 0
        self.fish_swimming = False
        # For within-bout checks:
        self.bout_start = None
        self.bout_stop = None

    def get_fish_vel(self):
        """ Function that update estimated fish velocty. Change to add lag or
        shunting.
        """
        self.fish_vel = self._experiment.estimator.get_velocity()

    def bout_started(self):
        """ Function called on bout start.
        """
        pass

    def bout_occurring(self):
        pass

    def bout_ended(self):
        """ Function called on bout end.
        """
        pass

    def update(self):
        self.get_fish_vel()

        # If estimated velocity greater than threshold
        # the fish is performing a bout:
        if self.fish_vel < self.swimming_threshold:
            self.fish_swimming = True

            if self.bout_start is None:
                # If here, we are at the beginning of a bout
                self.bout_start = self._elapsed
                self.bout_stop = None
                self.bout_started()

            self.bout_occurring()

        else:  # if not bouting:
            if self.bout_start is not None:
                # If here, we are at the end of a bout
                self.bout_stop = self._elapsed

                self.bout_ended()

                self.bout_start = None

            self.fish_swimming = False

        # Use method for calculating final velocity and update:
        self.calculate_final_vel()
        self.x += self._dt * self.vel

        super().update()

    def calculate_final_vel(self):
        self.vel = self.base_vel - self.fish_vel * int(self.fish_swimming)


class CalibratingClosedLoop1D(Basic_CL_1D):
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
            target_avg_fish_vel=-15,
            calibrate_after=5,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "calibrating_cl1D"
        self.dynamic_parameters.extend(["est_gain", "median_calib"])
        self.target_avg_fish_vel = target_avg_fish_vel  # target velocity for the calibration

        self.bout_counter = 0
        self.bout_peak_vel = 0
        self.calibrate_after = calibrate_after
        self.bouts_vig_list = []
        self.bout_vig = []
        self.median_vel = np.nan
        self.final_vel = np.nan
        self.median_calib = np.nan
        self.est_gain = 0

    def bout_started(self):
        self.est_gain = self._experiment.estimator.base_gain

    def bout_occurring(self):
        self.bout_vig.append(self.fish_vel/self.est_gain)

    def bout_ended(self):

        if self.bout_stop - self.bout_start > 0.2:
            self.bout_counter += 1

            # Update list with peak velocities and reset current peak vel:
            self.bouts_vig_list.append(np.median(self.bout_vig))

            # After some number of bouts, update estimator gain:
            if len(self.bouts_vig_list) > self.calibrate_after:
                self.median_vig = np.median(self.bouts_vig_list)
                self.median_calib = self.median_vig * self.est_gain
                self.est_gain = self.target_avg_fish_vel / self.median_vig

                self._experiment.estimator.base_gain = self.est_gain

        self.bout_vel = []

    def stop(self):
        if len(self.bouts_vig_list) > self.calibrate_after:
            self._experiment.logger.info(
                "Calibrated! Median speed achieved: {} with {} bouts".format(
                    self.median_calib, len(self.bouts_vig_list)))


class GainLagClosedLoop1D(Basic_CL_1D):

    def __init__(
        self,
        gain=1,
        lag=0,
        shunted=False,
        fixed_vel=None,
        gain_drop_start=None,
        gain_drop_end=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "gain_lag_cl1D"
        self.dynamic_parameters.extend(["gain", "lag"])
        self.lag = lag
        self.gain = gain
        self.shunted = shunted
        self.fixed_vel = fixed_vel  # fixed forward velocity
        self.gain_drop_start = gain_drop_start
        self.gain_drop_end = gain_drop_end

    def get_fish_vel(self):
        """ Function that update estimated fish velocty. Change to add lag or
        shunting.
        """
        super(GainLagClosedLoop1D, self).get_fish_vel()
        self.lag_vel = self._experiment.estimator.get_velocity(self.lag)

    def bout_started(self):
        """ Function called on bout start.
        """
        pass

    def bout_occurring(self):
        pass

    def bout_ended(self):
        """ Function called on bout end.
        """
        pass

    def calculate_final_vel(self):
        subtract_to_base = self.gain * self.lag_vel

        if self.gain_drop_start is not None and self.bout_start is not None:
            t = self._elapsed - self.bout_start
            if self.gain_drop_start < t < self.gain_drop_end:
                subtract_to_base = 0

        # Apply fish is swimming threshold, depending if shunted or not.
        if self.lag == 0 or self.shunted:
            subtract_to_base *= int(self.fish_swimming)
        else:
            subtract_to_base *= int(self.lag_vel < self.swimming_threshold)

        self.vel = self.base_vel - subtract_to_base


class AcuteClosedLoop1D(GainLagClosedLoop1D):

    def __init__(
            self,
            conditions_list=None,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "acute_cl1D"

        self.base_conditions = self.get_state()
        self.conditions_list = conditions_list
        self.acute_cond_weights = [c.get("w", 1/len(conditions_list))
                                   for c in conditions_list]

        self.current_condition = None

    def bout_started(self):
        """ Function called on bout start.
        """
        # reset to baseline values:
        if self.current_condition is not None:
            for k in self.current_condition["change_to"].keys():
                self.__setattr__(k, self.base_conditions[k])

        # chose one condition:
        self.current_condition = choices(self.conditions_list,
                                         self.acute_cond_weights)[0]

        for k, v in self.current_condition["change_to"].items():
            # print("setting: {} gain and {} lag".format(self.gain, self.lag))
            self.__setattr__(k, v)
            # print("set: {} gain and {} lag".format(self.gain, self.lag))

        # refresh lag if it was changed:
        self.lag_vel = self._experiment.estimator.get_velocity(self.lag)


    def update(self):
        """ Function called on bout end.
        """
        super().update()




    # def update(self):
    #     """
    #     Here we use fish velocity to change velocity of gratings.
    #     """
    #     super().update()
    #
    #     self.fish_vel = self._experiment.estimator.get_velocity(lag=self.lag)
    #
    #     if self.base_vel == 0:
    #         self.shunted = False
    #         self.fish_swimming = False
    #
    #     if (
    #         self.shunting
    #         and self.fish_swimming
    #         and self.fish_vel > self.swimming_threshold
    #     ):
    #         self.shunted = True
    #
    #     # If estimated velocity greater than threshold
    #     # the fish is performing a bout:
    #     if self.fish_vel < self.swimming_threshold:  # if bouting:
    #         self.fish_swimming = True
    #
    #         if self.bout_start is None:
    #             self.bout_start = self._elapsed
    #         self.bout_stop = None
    #     else:  # if not bouting:
    #         self.bout_start = None
    #         if self.bout_stop is None:
    #             self.bout_stop = self._elapsed
    #
    #         self.fish_swimming = False
    #
    #     if self.fixed_vel is None:
    #         self.vel = int(not self.shunted) * (
    #             self.base_vel - self.fish_vel * self.gain * int(self.fish_swimming)
    #         )
    #     else:
    #         if self.fish_swimming and not self.base_vel == 0:
    #             self.vel = self.fixed_vel
    #         else:
    #             self.vel = self.base_vel
    #
    #
    #     self.x += self._dt * self.vel


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

