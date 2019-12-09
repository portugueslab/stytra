import numpy as np
from PyQt5.QtGui import QTransform

try:
    from random import choices
except ImportError:
    print("Cannot import choices!")

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    PositionStimulus,
    InterpolatedStimulus,
    Stimulus,
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
        max_interbout_time: float
            if not None, maximum time allowed without any bout detected, after
            which the experiment is aborted
        """

    def __init__(
        self,
        *args,
        base_vel=10,
        swimming_threshold=-2,
        max_fish_vel=40,
        max_interbout_time=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "general_cl1D"
        self.dynamic_parameters.extend(["vel", "base_vel", "fish_swimming"])
        self.base_vel = base_vel  # base grating velocity
        self.vel = base_vel  # final grating velocity

        self.swimming_threshold = swimming_threshold
        self.max_fish_vel = max_fish_vel

        self.fish_vel = 0
        self.fish_swimming = False
        # For within-bout checks:
        self.bout_start = np.nan
        self.bout_stop = np.nan
        self.max_interbout_time = max_interbout_time
        self.prev_bout_t = 0

    def get_fish_vel(self):
        """ Function that update estimated fish velocty. Change to add lag or
        shunting.
        """
        self.fish_vel = self._experiment.estimator.get_velocity()

    def bout_started(self):
        """ Function called on bout start.
        """
        self.prev_bout_t = self._elapsed

    def bout_occurring(self):
        pass

    def bout_ended(self):
        """ Function called on bout end.
        """
        pass

    def update(self):
        if self.max_interbout_time is not None:
            if self._elapsed - self.prev_bout_t > self.max_interbout_time:
                self._experiment.logger.info(
                    "Experiment aborted! {} seconds without bouts".format(
                        self._elapsed - self.prev_bout_t
                    )
                )
                self.abort_experiment()

        self.get_fish_vel()

        # If estimated velocity greater than threshold
        # the fish is performing a bout:
        if self.fish_vel < self.swimming_threshold:
            self.fish_swimming = True

            if np.isnan(self.bout_start):
                # If here, we are at the beginning of a bout
                self.bout_start = self._elapsed
                self.bout_stop = np.nan
                self.bout_started()

            self.bout_occurring()

        else:  # if not bouting:
            if not np.isnan(self.bout_start):
                # If here, we are at the end of a bout
                self.bout_stop = self._elapsed

                self.bout_ended()

                self.bout_start = np.nan

            self.fish_swimming = False

        # Use method for calculating final velocity and update:
        self.calculate_final_vel()
        self.x += self._dt * self.vel

        super().update()

    def calculate_final_vel(self):
        self.vel = self.base_vel - self.fish_vel * int(self.fish_swimming)

    def abort_experiment(self):
        self._experiment.protocol_runner.stop()


class CalibratingClosedLoop1D(Basic_CL_1D):
    """
    Special closed-loop class that adjust vigor estimator gain value until
    fish velocity achieved matches a specified target value.
    The experiment is automatically aborted if not enough bouts are performed or
    if the gain value is outside a normal range.

    Parameters
    ----------
    target_avg_fish_vel: float
        target fish velocity, in mm/s
    calibrate_after: int
        minimum number of bouts after which calibration happens.
    min_bout_n: int
        minimum number of performed bouts
    valid_gain_range: tuple
        (min, max) values for the final gain to be considered valid
    """

    def __init__(
        self, target_avg_fish_vel=-15, calibrate_after=5, min_bout_n=30, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "calibrating_cl1D"
        self.dynamic_parameters.extend(["est_gain", "median_calib"])
        self.target_avg_fish_vel = (
            target_avg_fish_vel
        )  # target velocity for the calibration

        self.bout_counter = 0
        self.bout_peak_vel = 0
        self.calibrate_after = calibrate_after
        self.bouts_vig_list = []
        self.bout_vig = []
        self.median_vel = np.nan
        self.final_vel = np.nan
        self.median_calib = np.nan
        self.est_gain = 0
        self.min_bout_n = 30
        self.valid_gain_range = (-40, -10)
        self.min_bout_duration = 0.2

    def bout_started(self):
        super().bout_started()
        self.est_gain = self._experiment.estimator.base_gain

    def bout_occurring(self):
        self.bout_vig.append(self.fish_vel / self.est_gain)

    def bout_ended(self):

        if self.bout_stop - self.bout_start > self.min_bout_duration:
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
        if (
            len(self.bouts_vig_list) < self.min_bout_n
            or self.est_gain > self.valid_gain_range[1]
            or self.est_gain < self.valid_gain_range[0]
        ):
            self.abort_experiment()

            self._experiment.logger.info(
                "Experiment aborted! N bouts: {}; gain: {}".format(
                    len(self.bouts_vig_list), self.est_gain
                )
            )

        if len(self.bouts_vig_list) > self.calibrate_after:
            self._experiment.logger.info(
                "Calibrated! Calculated gain  {} with {} bouts".format(
                    self.est_gain, len(self.bouts_vig_list)
                )
            )


class GainChangerStimulus(Stimulus):
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

    def __init__(self, newgain=1):
        self.duration = 0.001
        super().__init__()
        self.name = "fix_gain_calibration_cl1D"
        self.newgain = newgain

    def start(self):
        self._experiment.estimator.base_gain = self.newgain


class GainLagClosedLoop1D(Basic_CL_1D):
    def __init__(
        self,
        gain=1,
        lag=0,
        shunted=False,
        fixed_vel=np.nan,
        gain_drop_start=np.nan,
        gain_drop_end=np.nan,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "gain_lag_cl1D"
        self.dynamic_parameters.extend(
            ["gain", "lag", "gain_drop_start", "gain_drop_end", "shunted"]
        )
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

    def calculate_final_vel(self):
        subtract_to_base = self.gain * self.lag_vel

        if not np.isnan(self.gain_drop_start) and not np.isnan(self.bout_start):
            t = self._elapsed - self.bout_start
            if self.gain_drop_start <= t < self.gain_drop_end:
                subtract_to_base = 0

        # Apply fish is swimming threshold, depending if shunted or not.
        if self.lag == 0 or self.shunted:
            subtract_to_base *= int(self.fish_swimming)
        else:
            subtract_to_base *= int(self.lag_vel < self.swimming_threshold)

        self.vel = self.base_vel - subtract_to_base


class AcuteClosedLoop1D(GainLagClosedLoop1D):
    def __init__(self, conditions_list=None, **kwargs):
        super().__init__(**kwargs)
        self.name = "acute_cl1D"

        self.base_conditions = self.get_state()
        self.conditions_list = conditions_list
        self.acute_cond_weights = [
            c.get("w", 1 / len(conditions_list)) for c in conditions_list
        ]

        self.current_condition = None

    def bout_started(self):
        """ Function called on bout start.
        """
        super().bout_started()
        # reset to baseline values:
        if self.current_condition is not None:
            for k in self.current_condition["change_to"].keys():
                self.__setattr__(k, self.base_conditions[k])

        # chose one condition:
        self.current_condition = choices(self.conditions_list, self.acute_cond_weights)[
            0
        ]

        for k, v in self.current_condition["change_to"].items():
            # print("setting: {} gain and {} lag".format(self.gain, self.lag))
            self.__setattr__(k, v)
            # print("set: {} gain and {} lag".format(self.gain, self.lag))

        # refresh lag if it was changed:
        self.lag_vel = self._experiment.estimator.get_velocity(self.lag)


class PerpendicularMotion(BackgroundStimulus, InterpolatedStimulus):
    """ A stimulus which is always kept perpendicular to the fish

    """

    def update(self):
        y, x, theta = self._experiment.estimator.get_position()
        if np.isfinite(theta):
            self.theta = theta
        super().update()


class FishTrackingStimulus(PositionStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("is_tracking")
        self.is_tracking = True

    def update(self):
        if self.is_tracking:
            y, x, theta = self._experiment.estimator.get_position()
            if np.isfinite(theta):
                self.x = x
                self.y = y
                self.theta = theta
        super().update()


class FishRelativeStimulus(BackgroundStimulus):
    def get_transform(self, w, h, x, y):
        y_fish, x_fish, theta_fish = self._experiment.estimator.get_position()
        if np.isnan(y_fish):
            return super().get_transform(w, h, x, y)
        rot_fish = (theta_fish - np.pi / 2) * 180 / np.pi
        return super().get_transform(w, h, x, y) * (
            QTransform().translate(x_fish, y_fish).rotate(rot_fish)
        )
