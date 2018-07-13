import numpy as np

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    SeamlessImageStimulus,
    CircleStimulus,
    MovingGratingStimulus,
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
        the freely-swimming behaviour
    lag:
        how much extra delay is provided in the closed loop
    shunting: bool
        if true, when the fish stops swimming its infulence on the
        background motion stops, immediately independent of lag
    swimming_threshold: float
        the velocity at which the fish is considered to be performing
        a bout
    df_param: (optional) DataFrame
        the dataframe which specifies the temporal dynamics of the previously
        described parameters
    """

    def __init__(
        self,
        *args,
        base_vel=10,
        gain=1,
        lag=0,
        shunting=False,
        swimming_threshold=0.2 * -30,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.name = "closed loop 1D"
        self.fish_velocity = 0
        self.dynamic_parameters = ["vel", "fish_velocity", "gain"]
        self.base_vel = base_vel
        self.fish_velocity = 0
        self.vel = base_vel
        self.lag = lag
        self.gain = gain
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
        super().update()

        self.fish_velocity = self._experiment.estimator.get_velocity(lag=self.lag)

        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if (
            self.shunting
            and self.fish_swimming
            and self.fish_velocity > self.swimming_threshold
        ):
            self.shunted = True

        # If estimated velocity greater than threshold
        # the fish is performing a bout
        if self.fish_velocity < self.swimming_threshold:
            self.fish_swimming = True

            if self.bout_start is None:
                self.bout_start = self._elapsed
            self.bout_stop = None
        else:
            self.bout_start = None
            if self.bout_start is None:
                self.bout_start = self._elapsed

            self.fish_swimming = False

        self.vel = int(not self.shunted) * (
            self.base_vel - self.fish_velocity * self.gain * int(self.fish_swimming)
        )

        if self.vel is None or self.vel > 50:
            self.vel = 0

        self.x += self._dt * self.vel


class TrackingStimulus(CircleStimulus):
    def update(self):
        self.x, self.y, _ = self._experiment.estimator.get_position()
        super().update()
