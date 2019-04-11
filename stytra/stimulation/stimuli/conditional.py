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
    """ A wrapper for stimuli which switches between two stimuli dependending on
    conditions: an on condition defined in the check_condition_on method
    and an off condition defined check_condition_on

    Parameters
    ----------
    stim_on: Stimulus
    stim_off: Stimulus
    reset_phase: bool
        whether to reset the phase of an InterpolatedStimulus if it goes from on to off
    reset_phase_shift: int
        when the stim_on reappears and reset_phase is true, we can set this to 0,
        which resets the stim_on to the state at the beginning of the current phase,
        1 to go to the next phase or -1 to go to the previous phase.
    reset_to_mod_phase: tuple (int, int), optional, default None
        if the stim_on consists of paired phases (e.g. motion on, motion off), it can
        one can reset to the begging of the bigger phase.
        If the stimulation pattern is e.g. [no_motion, motion_left, motion_right] to
        always get to no_motion on reenter reset_to_mod_phase would be set to (0, 3)
        This paremeter can be combined with reset_phase_shift, but in usual cases it
        has to be set to 0

    """
    def __init__(
        self,
        stim_on,
        stim_off,
        reset_phase=False,
        reset_phase_shift=0,
        reset_to_mod_phase=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = "conditional"
        self._stim_off = stim_off
        self._stim_on = stim_on
        self.active = self._stim_off
        self._elapsed_difference = 0
        self._elapsed_when_centering_started = 0
        self.reset_phase = reset_phase
        self.reset_phase_shift = reset_phase_shift
        self.reset_to_mod_phase = reset_to_mod_phase

        self.on = False
        self.dynamic_parameters.append("on")

        self.duration = self._stim_on.duration
        self.stimulus_dynamic = hasattr(stim_on, "dynamic_parameters")
        self._dt = 0
        self._past_t = 0
        self._previous_value = False

    @property
    def dynamic_parameter_names(self):
        if self.stimulus_dynamic:
            return (
                super().dynamic_parameter_names + self._stim_on.dynamic_parameter_names
            )
        else:
            return super().dynamic_parameter_names

    def get_dynamic_state(self):
        state = super().get_dynamic_state()
        if self.stimulus_dynamic and self.on:
            state.update(self._stim_on.get_dynamic_state())
        return state

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        self._stim_on.initialise_external(experiment)
        self._stim_off.initialise_external(experiment)

    def get_state(self):
        state = super().get_state()
        state.update({"On": self._stim_on.get_state(),
                      "Off": self._stim_off.get_state()})
        return state

    def start(self):
        super().start()
        self._stim_on.start()
        self._stim_off.start()

    def check_condition_on(self):
        return True

    def check_condition_off(self):
        return True

    def update(self):
        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed

        # check if the state switched
        if self._previous_value and self.check_condition_off():
            self.on = False
            self.active = self._stim_off

        elif not self._previous_value and self.check_condition_on():
            self.on = True
            self.active = self._stim_on

            if self.reset_phase:
                new_phase = max(self.active.current_phase +
                                  self.reset_phase_shift, 0)
                if self.reset_to_mod_phase is not None:
                    outer_phase = new_phase // self.reset_to_mod_phase[1]
                    new_phase = outer_phase * self.reset_to_mod_phase[1] + \
                                  self.reset_to_mod_phase[0]
                time_added = (
                        self._elapsed
                        - self._elapsed_difference
                        - self.active.phase_times[new_phase]
                )
                self.duration += time_added
                self._elapsed_difference += time_added

        # update the current stimulus
        if self.on:
            self.active._elapsed = self._elapsed - self._elapsed_difference
        else:
            self.duration += self._dt
            self.active.duration += self._dt
            self._elapsed_difference += self._dt
            self.active._elapsed = self._elapsed

        self._previous_value = self.on
        self.active.update()

    def paint(self, p, w, h):
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawRect(QRect(-1, -1, w + 2, h + 2))
        self.active.paint(p, w, h)


class SingleConditionalWrapper(ConditionalWrapper):
    def chceck_condition_off(self):
        return not self.check_condition_on()


class CenteringWrapper(SingleConditionalWrapper):
    """ A wrapper which shows the centering stimulus (radial gratings)
        when the fish exits a given radius from the display center

        Parameters
        ----------
        stimulus: Stimlus
            the stimulus to be displayed when not centering

        centering_stimulus: Stimulus, optional
            by default radial gratings

        margin: float
            the centering activating radius in mm


        **kwargs
            other arguments supplied to :class:`ConditionalStimulus`

        """
    def __init__(self, stimulus, *args, centering_stimulus=None, margin=45,
                 **kwargs):
        super().__init__(*args, stim_on=stimulus,
                         stim_off=centering_stimulus or RadialSineStimulus(duration=stimulus.duration),
                         **kwargs)
        self.name = "centering"
        self.margin = margin ** 2
        self.xc = 320
        self.yc = 240

    def check_condition_on(self):
        y, x, theta = self._experiment.estimator.get_position()
        scale = self._experiment.calibrator.mm_px ** 2
        return (x > 0 and ((x - self.xc) ** 2 + (y - self.yc) ** 2) <=
                self.margin / scale)

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        super().paint(p, w, h)


class TwoRadiusCenteringWrapper(ConditionalWrapper):
    """ An extension of the :class:`CenteringWrapper` that takes two radii,
    a smaller one, to stop the centering stimulus, and a bigger one to start
    it again

    Parameters
    ----------
    stimulus: Stimlus
        the stimulus to be displayed when not centering

    centering_stimulus: Stimulus, optional
        by default radial gratings

    r_out: float
        the centering activating radius in mm

    r_in: float
        the centering deactivating radius in mm

    **kwargs
        other arguments supplied to :class:`ConditionalStimulus`

    """
    def __init__(self, stimulus, *args, centering_stimulus=None, r_out=45,
                 r_in=20,
                 **kwargs):
        super().__init__(*args, stim_on=stimulus,
                         stim_off=(centering_stimulus or RadialSineStimulus(
                             duration=stimulus.duration)),
                         **kwargs)
        self.name = "centering"
        self.margin_in = r_in ** 2
        self.margin_out = r_out ** 2
        self.xc = 320
        self.yc = 240

    def check_condition_on(self):
        y, x, theta = self._experiment.estimator.get_position()
        scale = self._experiment.calibrator.mm_px **2
        return ((not np.isnan(x)) and (
                    (x - self.xc) ** 2 + (y - self.yc) ** 2 <= self.margin_in
                    / scale))

    def check_condition_off(self):
        y, x, theta = self._experiment.estimator.get_position()
        scale = self._experiment.calibrator.mm_px ** 2
        return (np.isnan(x) or
                ((x - self.xc) ** 2 + (y - self.yc) ** 2 > self.margin_out /
                 scale))

    def paint(self, p, w, h):
        self.xc, self.yc = w / 2, h / 2
        super().paint(p, w, h)
