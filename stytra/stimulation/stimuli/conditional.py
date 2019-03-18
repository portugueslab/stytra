import numpy as np
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor
from stytra.stimulation.stimuli.generic_stimuli import DynamicStimulus
from stytra.stimulation.stimuli.visual import RadialSineStimulus


class PauseOutsideStimulus(DynamicStimulus):
    def __init__(
        self,
        stim,
        reset_phase=0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "conditional"
        self.active = stim
        self._elapsed_difference = 0
        self._elapsed_when_centering_started = 0
        self.reset_phase = reset_phase

        self.value = False
        self.dynamic_parameters.append("value")

        self.duration = self.active.duration
        self.stimulus_dynamic = hasattr(stim, "dynamic_parameters")
        self._dt = 0
        self._past_t = 0
        self._previous_value = False

    @property
    def dynamic_parameter_names(self):
        if self.stimulus_dynamic:
            return (
                super().dynamic_parameter_names +
                self.active.dynamic_parameter_names
            )
        else:
            return super().dynamic_parameter_names

    def get_dynamic_state(self):
        state = super().get_dynamic_state()
        if self.stimulus_dynamic and self.value:
            state.update(self.active.get_dynamic_state())
        return state

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self.active.initialise_external(experiment)

    def get_state(self):
        state = super().get_state()
        state.update({"stim": self.active.get_state()})
        return state

    def start(self):
        super().start()
        self.active.start()

    def check_condition(self):
        y, x, theta = self._experiment.estimator.get_position()
        return not np.isnan(y)

    def update(self):
        super().update()

        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed
        if not self.check_condition():
            self.value = False
            self.duration += self._dt
            self.active.duration += self._dt
            self._elapsed_difference += self._dt
        else:
            if self.reset_phase > 0 and not self._previous_value:
                phase_reset = max(self.active.current_phase -
                                  (self.reset_phase - 1), 0)
                self.active._elapsed = self.active.phase_times[phase_reset]
                time_added = (
                    self._elapsed
                    - self._elapsed_difference
                    - self.active.phase_times[phase_reset]
                )
                self.duration += time_added
                self._elapsed_difference += time_added
                self.value = True

        self.active._elapsed = self._elapsed - self._elapsed_difference
        self._previous_value = self.value
        self.active.update()

    def paint(self, p, w, h):
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        self.active.paint(p, w, h)


class ConditionalWrapper(DynamicStimulus):
    """ A meta-stimulus which switches stimuli when a condition is fulfilled

    Parameters
    ----------
    reset_phase: int
        If we want to reset the phase of the stimulus when it reappears this
        has to be bigger than 1, if we want to go back two phases we set it to
        2 and so on.

    reset_to_mod_phase: tuple (int, int) or None (default)
        E.g. if we want to reset to even phases (pauses) of a stimulus which consits of pauses
        and motions
        If using this parameter, reset_phase should be set to 1.


    """

    def __init__(
        self,
        stim_true,
        stim_false,
        reset_phase=0,
        reset_to_mod_phase=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "conditional"
        self._stim_false = stim_false
        self._stim_true = stim_true
        self.active = self._stim_false
        self._elapsed_difference = 0
        self._elapsed_when_centering_started = 0
        self.reset_phase = reset_phase
        self.reset_to_mod_phase = reset_to_mod_phase

        self.value = False
        self.dynamic_parameters.append("value")

        self.duration = self._stim_true.duration
        self.stimulus_dynamic = hasattr(stim_true, "dynamic_parameters")
        self._dt = 0
        self._past_t = 0
        self._previous_value = False

    @property
    def dynamic_parameter_names(self):
        if self.stimulus_dynamic:
            return (
                super().dynamic_parameter_names + self._stim_true.dynamic_parameter_names
            )
        else:
            return super().dynamic_parameter_names

    def get_dynamic_state(self):
        state = super().get_dynamic_state()
        if self.stimulus_dynamic and self.value:
            state.update(self._stim_true.get_dynamic_state())
        return state

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self._stim_true.initialise_external(experiment)
        self._stim_false.initialise_external(experiment)

    def get_state(self):
        state = super().get_state()
        state.update({"True": self._stim_true.get_state(),
                "False": self._stim_false.get_state()})
        return state

    def start(self):
        super().start()
        self._stim_true.start()
        self._stim_false.start()

    def check_condition(self):
        return True

    def update(self):
        super().update()

        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed
        if not self.check_condition():
            self.value = False
            self.active = self._stim_false
            self.duration += self._dt
            self.active.duration += self._dt
            self._elapsed_difference += self._dt
            self.active._elapsed = self._elapsed
        else:
            self.active = self._stim_true
            if self.reset_phase > 0 and not self._previous_value:
                phase_reset = max(self.active.current_phase -
                                  (self.reset_phase - 1), 0)
                if self.reset_to_mod_phase is not None:
                    outer_phase = phase_reset // self.reset_to_mod_phase[1]
                    phase_reset = outer_phase * self.reset_to_mod_phase[1] + self.reset_to_mod_phase[0]
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

            self.value = True

        self._previous_value = self.value
        self.active.update()

    def paint(self, p, w, h):
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        self.active.paint(p, w, h)


class CenteringWrapper(ConditionalWrapper):
    def __init__(self, stimulus, *args, centering_stimulus=None, margin=400, **kwargs):
        super().__init__(*args, stim_true=stimulus,
                         stim_false=centering_stimulus or RadialSineStimulus(duration=stimulus.duration),
                         **kwargs)
        self.name = "centering"
        self.margin = margin ** 2
        self.xc = 320
        self.yc = 240

    def check_condition(self):
        y, x, theta = self._experiment.estimator.get_position()
        return (x > 0 and ((x - self.xc) ** 2 + (y - self.yc) ** 2) <= self.margin)

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        super().paint(p, w, h)


class DoubleConditionalWrapper(ConditionalWrapper):
    """ An extension of the conditional wrapper where there can be two conditions,
    one for stimulus being turned on, and a different one for off.

    """

    def check_condition_on(self):
        return True

    def check_condition_off(self):
        return True

    def update(self):
        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed

        # check if the state switched
        if self._previous_value and self.check_condition_off():
            self.value = False
            self.active = self._stim_false

        elif not self._previous_value and self.check_condition_on():
            self.value = True
            self.active = self._stim_true
            phase_reset = max(self.active.current_phase -
                              (self.reset_phase - 1), 0)
            if self.reset_to_mod_phase is not None:
                outer_phase = phase_reset // self.reset_to_mod_phase[1]
                phase_reset = outer_phase * self.reset_to_mod_phase[1] + \
                              self.reset_to_mod_phase[0]
            time_added = (
                    self._elapsed
                    - self._elapsed_difference
                    - self.active.phase_times[phase_reset]
            )
            self.duration += time_added
            self._elapsed_difference += time_added

        # update the current stimulus
        if self.value:
            self.active._elapsed = self._elapsed - self._elapsed_difference
        else:
            self.duration += self._dt
            self.active.duration += self._dt
            self._elapsed_difference += self._dt
            self.active._elapsed = self._elapsed

        self._previous_value = self.value
        self.active.update()


class TwoRadiusCenteringWrapper(DoubleConditionalWrapper):
    def __init__(self, stimulus, *args, centering_stimulus=None, r_out=400,
                 r_in=100,
                 **kwargs):
        super().__init__(*args, stim_true=stimulus,
                         stim_false=centering_stimulus or RadialSineStimulus(duration=stimulus.duration),
                         **kwargs)
        self.name = "centering"
        self.margin_in = r_in ** 2
        self.margin_out = r_out ** 2
        self.xc = 320
        self.yc = 240

    def check_condition_on(self):
        y, x, theta = self._experiment.estimator.get_position()
        return ((not np.isnan(x)) and (
                    (x - self.xc) ** 2 + (y - self.yc) ** 2 <= self.margin_in))

    def check_condition_off(self):
        y, x, theta = self._experiment.estimator.get_position()
        return (np.isnan(x) or
                ((x - self.xc) ** 2 + (y - self.yc) ** 2 > self.margin_out))

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        super().paint(p, w, h)