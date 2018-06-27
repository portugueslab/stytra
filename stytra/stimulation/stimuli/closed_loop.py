import numpy as np

from stytra.stimulation.stimuli import (
    DynamicStimulus,
    BackgroundStimulus,
    SeamlessImageStimulus,
    CircleStimulus,
    SeamlessGratingStimulus
)


class ClosedLoop1D(BackgroundStimulus, DynamicStimulus):
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
        self.dynamic_parameters.append("vel")
        self.dynamic_parameters.append("fish_velocity")
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

        self._past_x = self.x
        self._past_y = self.y
        self._past_theta = self.theta
        self._past_t = 0

    def update(self):
        """
        Here we use fish velocity to change velocity of gratings.
        """
        super().update()
        dt = (self._elapsed - self._past_t)

        self.fish_velocity = self._experiment.estimator.get_velocity()
        # print('fish_velocity: {}'.format(self.fish_velocity))
        if self.base_vel == 0:
            self.shunted = False
            self.fish_swimming = False

        if self.shunting and self.fish_swimming and self.fish_velocity < self.swimming_threshold:
            self.shunted = True

        # If estimated velocity greater than threshold we are in a bout
        if self.fish_velocity > self.swimming_threshold:
            print('fish_swimming!')
            self.going = 1
            self.fish_swimming = True
            if self.bout_start is None:
                self.bout_start = self._elapsed
            self.bout_stop = None
        else:
            self.going = 0
            self.bout_start = None
            if self.bout_start is None:
                self.bout_start = self._elapsed

            self.fish_swimming = False

        self.vel = int(not self.shunted) * (self.base_vel -
                   self.fish_velocity * self.gain * self.base_gain * int(self.fish_swimming))
        # print('{} - {}'.format(int(not self.shunted), self.fish_velocity * self.gain * self.base_gain * int(self.fish_swimming)))
        # print('velocity: {}'.format(self.vel))
        if self.vel is None or self.vel > 50:
            print('I am resetting vel to 0 because it is strange.')
            self.vel = 0

        prev_x = self.x
        self.x += dt * self.vel
        # print('Prev. x: {}; vel: {}; new_x: {}'.format(prev_x, self.vel,
        #                                                self.x))
        # TODO implement lag
        self._past_t = self._elapsed
        for attr in ['x', 'y', 'theta']:
            try:
                setattr(self, 'past_'+attr, getattr(self, attr))
            except (AttributeError, KeyError):
                pass


class ClosedLoop1DGratings(ClosedLoop1D, SeamlessGratingStimulus):
    def __init__(
        self,
        df_base_vel,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.duration = float(df_base_vel.t.iat[-1])
        self.df_base_vel = df_base_vel

    def update(self):
    #     """ """
    #     # to use parameters defined as velocities, we need the time
    #     # difference before previous display
        self.base_vel = np.interp(self._elapsed, self.df_base_vel.t, self.df_base_vel.vel)
        super().update()

        # for col in self.df_param.columns:
        #     if col != "t":
        #         # for defined velocities, integrates the parameter
        #         if col.startswith("vel_"):
        #             setattr(
        #                 self,
        #                 col[4:],
        #                 getattr(self, col[4:])
        #                 + dt
        #                 * np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
        #             )
        #         # otherwise it is set by interpolating the column of the
        #         # dataframe
        #         else:
        #             setattr(
        #                 self,
        #                 col,
        #                 np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
        #             )
        #
        # # the time of refresh is saved to calculate the differences
        # self._past_t = self._elapsed

#
# class ClosedLoop1DGratings(SeamlessGratingStimulus):
#     """
#     """
#     def __init__(self, *args, default_velocity=0, gain=1,
#                  shunting=True,
#                  base_gain=-30,
#                  swimming_threshold=0.2,
#                  lag=0.1,
#                  **kwargs):
#         super().__init__(*args, **kwargs)
#         self.x = 0
#         self.y = 0
#         self.going = 0
#         self.lag = lag
#         self.name = 'closed loop 1D'
#         self.dynamic_parameters.append('vel')
#         self.dynamic_parameters.append('x')
#         self.dynamic_parameters.append('fish_velocity')
#         self.dynamic_parameters.append('going')
#         self.dynamic_parameters.append('delay_bool')
#         self.base_vel = default_velocity
#         self.fish_velocity = 0
#         self.vel = 0
#         self.gain = gain
#         self.base_gain = base_gain
#         self.swimming_threshold = swimming_threshold
#         self.fish_swimming = False
#         self.shunting = shunting
#         self.shunted = False
#
#         self.bout_start = None
#         self.bout_stop = None
#
#         self._past_x = self.x
#         self._past_y = self.y
#         self._past_theta = self.theta
#         self._past_t = 0
#
#     def update(self):
#         """
#         Here we use fish velocity to change velocity of gratings.
#         """
#         super().update()
#         dt = (self._elapsed - self._past_t)
#         self.fish_velocity = \
#             self._experiment.fish_motion_estimator.get_velocity(
#                 lag=self.lag)
#         # print('fish_velocity: {}'.format(self.fish_velocity))
#         if self.base_vel == 0:
#             self.shunted = False
#             self.fish_swimming = False
#
#         if self.shunting and self.fish_swimming and self.fish_velocity < self.swimming_threshold:
#             self.shunted = True
#
#         # If estimated velocity greater than threshold we are in a bout
#         if self.fish_velocity > self.swimming_threshold:
#             # pass
#             self.going = 1
#             self.fish_swimming = True
#             if self.bout_start is None:
#                 self.bout_start = self._elapsed
#             self.bout_stop = None
#         else:
#             self.going = 0
#             self.bout_start = None
#             if self.bout_start is None:
#                 self.bout_start = self._elapsed
#
#             self.fish_swimming = False
#
#         self.vel = int(not self.shunted) * (self.base_vel -
#                    self.fish_velocity * self.gain * self.base_gain * int(self.fish_swimming))
#
#         print('velocity: {}'.format(self.vel))
#         if self.vel is None or self.vel > 50:
#             print('I am resetting vel to 0 because it is strange.')
#             self.vel = 0
#
#         prev_x = self.x
#         self.x += dt * self.vel
#         print('Prev. x: {}; vel: {}; new_x: {}'.format(prev_x, self.vel,
#                                                        self.x))
#         # TODO implement lag
#         self._past_t = self._elapsed
#         for attr in ['x', 'y', 'theta']:
#             try:
#                 setattr(self, 'past_'+attr, getattr(self, attr))
#             except (AttributeError, KeyError):
#                 pass
#
# #


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
