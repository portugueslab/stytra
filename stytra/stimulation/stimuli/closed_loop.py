from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor

import numpy as np

try:
    from random import choices
except ImportError:
    print("Cannot import choiches!")

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
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
        self, *args, base_vel=10, swimming_threshold=-2, max_fish_vel=40, **kwargs
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

    def __init__(self, target_avg_fish_vel=-15, calibrate_after=5, **kwargs):
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

    def bout_started(self):
        self.est_gain = self._experiment.estimator.base_gain

    def bout_occurring(self):
        self.bout_vig.append(self.fish_vel / self.est_gain)

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
                    self.median_calib, len(self.bouts_vig_list)
                )
            )


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
            if self.gain_drop_start < t < self.gain_drop_end:
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


class ConditionalWrapper(DynamicStimulus):
    """ A meta-stimulus which turns on centering if the fish
    veers too much towrds the edge

    """

    def __init__(
        self,
        stim_true,
        stim_false,
        pause_stimulus=False,
        reset_phase=0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "conditional"
        self.stim_false = stim_false
        self.stim_true = stim_true
        self.active = self.stim_true
        self._elapsed_difference = 0
        self._elapsed_when_centering_started = 0
        self.pause_stimulus = pause_stimulus
        self.reset_phase = reset_phase

        self.on = False
        self.dynamic_parameters.append("centering_on")

        self.duration = self.stim_true.duration
        self.stimulus_dynamic = hasattr(stim_true, "dynamic_parameters")
        self._dt = 0
        self._past_t = 0
        self._was_centering = False

    @property
    def dynamic_parameter_names(self):
        if self.stimulus_dynamic:
            return (
                super().dynamic_parameter_names + self.stim_true.dynamic_parameter_names
            )
        else:
            return super().dynamic_parameter_names

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.stim_true.initialise_external(experiment)
        self.stim_false.initialise_external(experiment)

    def get_state(self):
        return self.stim_true.get_state()

    def start(self):
        super().start()
        self.stim_true.start()
        self.stim_false.start()

    def get_dynamic_state(self):
        state = super().get_dynamic_state()
        if self.stimulus_dynamic:
            state.update(self.stim_true.get_dynamic_state())
        return state

    def check_condition(self):
        return True

    def update(self):
        super().update()

        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed

        if self.check_condition():
            self.active = self.stim_false
            self.on = True
            self.duration += self._dt
            self.active.duration += self._dt
            self._elapsed_difference += self._dt
            self.active._elapsed = self._elapsed
        else:
            self.active = self.stim_true
            if self.reset_phase > 0 and self._was_centering:
                phase_reset = max(self.active.current_phase - (self.reset_phase - 1), 0)
                self.active._elapsed = self.active.phase_times[phase_reset]
                time_added = (
                    self._elapsed
                    - self._elapsed_difference
                    - self.active.phase_times[phase_reset]
                )
                self.duration += time_added
                self._elapsed_difference += time_added
            else:
                self.active._elapsed = self._elapsed - self._elapsed_difference

            self.on = False

        self._was_centering = self.on
        self.active.update()

    def paint(self, p, w, h):
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        self.active.paint(p, w, h)


class CenteringWrapper(ConditionalWrapper):
    def __init__(self, *args, margin=200, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "centering"
        self.margin = margin ** 2
        self.xc = 320
        self.yc = 240

    def check_condition(self):
        y, x, theta = self._experiment.estimator.get_position()
        return x > 0 and ((x - self.xc) ** 2 + (y - self.yc) ** 2) <= self.margin

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        super().paint(p, w, h)
