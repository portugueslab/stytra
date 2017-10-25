from stytra.stimulation.stimuli import Pause, \
    ShockStimulus, SeamlessGratingStimulus, VideoStimulus, \
    FullFieldPainterStimulus, ClosedLoop1D_variable_motion, \
    SeamlessWindmillStimulus, VRMotionStimulus
from stytra.stimulation.backgrounds import existing_file_background
import pandas as pd
import numpy as np
from stytra.stimulation.backgrounds import gratings
from stytra.collectors import Accumulator, HasPyQtGraphParams

from itertools import product

from copy import deepcopy


class Protocol(HasPyQtGraphParams):
    name = ''

    def __init__(self):
        super().__init__(name='stimulus_protocol_params')

        for child in self.params.children():
            self.params.removeChild(child)


        standard_params_dict = {'n_repeats': 1,
                                'pre_pause': 0.,
                                'post_pause': 0.}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stimulus_list(self):
        """Generate protocol from specified parameters
                """
        main_stimuli = self.get_stim_sequence()
        stimuli = []
        if self.params['pre_pause'] > 0:
            stimuli.append(Pause(duration=self.params['pre_pause']))

        for i in range(max(self.params['n_repeats'], 1)):
            stimuli.extend(deepcopy(main_stimuli))

        if self.params['post_pause'] > 0:
            stimuli.append(Pause(duration=self.params['post_pause']))

        return stimuli

    def get_stim_sequence(self):
        """ Get the stimulus list for each different protocol
        """
        return [Pause()]


class NoStimulation(Protocol):
    name = 'no_stimulation'

    def __init__(self, *args,  duration=60, **kwargs):
        """
        :param duration:
        """

        stimuli = []
        stimuli.append(Pause(duration=duration))  # change here for duration (in s)

        self.stimuli = stimuli
        self.current_stimulus = stimuli[0]
        super().__init__(*args, stimuli=stimuli, **kwargs)


class FlashProtocol(Protocol):
    name = 'flash protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'period_sec': 5.,
                                'flash_duration': 2.}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

        # self.set_new_param('period_sec', 5.)
        # self.set_new_param('flash_duration', 2.)

    def get_stim_sequence(self):
        stimuli = []

        stimuli.append(Pause(duration=self.params['period_sec'] - \
                                      self.params['flash_duration']))
        stimuli.append(FullFieldPainterStimulus(duration=self.params['flash_duration'],
                                                color=(255, 255, 255)))  # flash duration

        return stimuli


class Exp022Protocol(Protocol):
    name = "exp022 protocol"

    def __init__(self):
        super().__init__()

        standard_params_dict = {'windmill_amplitude': np.pi * 0.222,
                                'windmill_duration': 5.,
                                'windmill_arms_n': 8,
                                'windmill_freq': 0.2,
                                'inter_stim_pause': 5.,
                                'grating_period': 10,
                                'grating_vel': 10,
                                'grating_duration': 5.,
                                'flash_duration': 1.}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        stimuli = list()

        # ---------------
        # initial dark field:
        stimuli.append(Pause(duration=self.params['inter_stim_pause']))
        stim_color = (255, 0, 0)
        # ---------------
        # Gratings
        # Static gratings and three different velocities are implemented with a single
        # grating stimulus whose positions are specified for having the forward velocities:
        p = self.params['inter_stim_pause']
        s = self.params['grating_duration']
        v = self.params['grating_vel']
        # Grating tuple: t  x  theta
        dt_vel_tuple = [(0, 0, np.pi/2),  # set grid orientation to horizontal
                        (p, 0, np.pi/2),
                        (s, -0.3*v, np.pi/2),  # slow
                        (p, 0, np.pi/2),
                        (s, -v, np.pi/2),  # middle
                        (p, 0, np.pi/2),
                        (s, -3*v, np.pi/2),  # fast
                        (p, 0, np.pi/2),
                        (s, v, np.pi/2),  # backward
                        (p/2, 0, np.pi/2),
                        (0, 0, 0),  # change grid orientation to vertical
                        (p/2, 0, 0),
                        (s, v, 0),  # leftwards
                        (p, 0, 0),
                        (s, -v, 0),  # rightwards
                        (p/2, 0, 0)
                        ]

        t = [0]
        x = [0]
        theta = [0]
        for dt, vel, th in dt_vel_tuple:
            t.append(t[-1] + dt)
            x.append(x[-1] + dt * vel)
            theta.append(th)

        print(t)
        print(x)
        print(theta)

        # stimuli.append(SeamlessGratingStimulus(motion=pd.DataFrame(dict(t=t, x=x, theta=theta)),
        #                                        grating_period=self.params['grating_period'],
        #                                        color=stim_color))

        # ---------------
        # Windmill for OKR

        # create velocity dataframe. Velocity is sinusoidal and starts from 0:
        osc_time_vect = np.arange(0, self.params['windmill_duration'], 0.04)
        # Initial pause:
        t = [0, p / 2]
        theta = [self.params['windmill_amplitude']/2, ]*2  # initial pause

        # CW starting OKR:
        t.extend(t[-1] + osc_time_vect)
        theta.extend(np.cos(osc_time_vect * 2 * np.pi * self.params['windmill_freq']) * \
                     self.params['windmill_amplitude']/2)

        # Middle pause:
        t.extend([t[-1] + p])
        theta.extend([theta[-1]])

        # CCW starting OKR:
        t.extend(t[-1] + osc_time_vect)
        theta.extend(theta[-1] + self.params['windmill_amplitude']/2 - \
            np.cos(osc_time_vect * 2 * np.pi * self.params['windmill_freq']) * \
                     self.params['windmill_amplitude']/2)   # the offset avoid jumps in rotation

        # Final pause:
        t.extend([t[-1] + self.params['inter_stim_pause']])
        theta.extend([theta[-1]])  # initial pause

        print(t)
        print(theta)

        # Full field OKR:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t, theta=theta)),
                                                n_arms=self.params['windmill_arms_n'], color=stim_color))
        # Half-field left OKR:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t, theta=theta)),
                                                n_arms=self.params['windmill_arms_n'],
                                                clip_rect=(0, 0, 0.5, 1), color=stim_color))
        # Half-field right OKR:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t, theta=theta)),
                                                n_arms=self.params['windmill_arms_n'],
                                                clip_rect=(0.5, 0, 0.5, 1), color=stim_color))

        stimuli.append(Pause(duration=p/2))

        # ---------------
        # Final flashes:
        for i in range(4):
            stimuli.append(FullFieldPainterStimulus(duration=self.params['flash_duration'],
                                                    color=(255, 0, 0)))  # flash duration
            stimuli.append(Pause(duration=self.params['flash_duration']))  # flash duration

        stimuli.append(Pause(duration=p - self.params['flash_duration']))
        return stimuli


class VisualCodingProtocol(Protocol):
    name = "visual coding protocol"

    def __init__(self):
        super().__init__()

        standard_params_dict = {'video_file': r"3minUnderwater.mp4",
                                'n_directions': 8,
                                'n_split': 4,
                                'grating_period': 10.,
                                'grating_vel': 10.,
                                'part_field_duration': 1.,
                                'part_field_pause': 1.,
                                'inter_segment_pause': 2.,
                                'grating_move_duration': 2.,
                                'grating_pause_duration': 1.}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        stimuli = []

        n_split = 2 # self.params['n_split']

        for (ix, iy) in product(range(n_split), repeat=2):
            stimuli.append(FullFieldPainterStimulus(
                clip_rect=(
                    ix / n_split,
                    iy / n_split,
                    1 / n_split,
                    1 / n_split),
                duration=self.params['part_field_duration']))
            stimuli.append(Pause(duration=self.params['part_field_pause']))

        stimuli.append(Pause(duration=self.params['inter_segment_pause']))

        delta_theta = np.pi * 2 / self.params['n_directions']

        grating_motion = pd.DataFrame(dict(t=[0,
                                              self.params['grating_pause_duration'],
                                              self.params['grating_pause_duration'] + \
                                                        self.params['grating_move_duration'],
                                              self.params['grating_pause_duration'] * 2 + \
                                                        self.params['grating_move_duration']],
                                           x=[0,
                                              0,
                                              self.params['grating_move_duration'] * self.params['grating_vel'],
                                              self.params['grating_move_duration'] * self.params['grating_vel']]))

        for i_dir in range(self.params['n_directions']):
            stimuli.append(SeamlessGratingStimulus(duration=float(grating_motion.t.iat[-1]),
                                                   motion=grating_motion,
                                                   grating_period=self.params['grating_period'],
                                                   grating_angle=i_dir * delta_theta
                                                   ))

        stimuli.append(Pause(duration=self.params['inter_segment_pause']))

        # stimuli.append(VideoStimulus(video_path=video_file, duration=180))

        return stimuli


# class ShockProtocol(Protocol):
#     name = 'shock protocol'
#
#     def __init__(self, repetitions=10, period_sec=30, pre_stim_pause=20.95,
#                  prepare_pause=2, pyb=None):
#         """
#
#         :param repetitions:
#         :param prepare_pause:
#         :param pyb:
#         :param zmq_trigger:
#         """
#         super().__init__()
#
#         stimuli = []
#         # pre-shock interval
#         for i in range(repetitions):  # change here for number of trials
#             stimuli.append(Pause(duration=pre_stim_pause))
#             stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
#                                          pulse_n=1, pulse_dur_ms=5))
#             stimuli.append(Pause(duration=period_sec-pre_stim_pause))  # post flash interval
#
#         self.stimuli = stimuli
#         self.current_stimulus = stimuli[0]
#         self.name = 'shock'

#
# class FlashShockProtocol(Protocol):
#     name = 'Flash and shock'
#
#     def __init__(self, *args, period_sec=30, duration_sec=1, pre_stim_pause=20, shock_duration=0.05,
#                  pyb=None, zmq_trigger=None, **kwargs):
#         """
#
#         :param repetitions:
#         :param prepare_pause:
#         :param pyb:
#         :param zmq_trigger:
#         """
#         if not zmq_trigger:
#             print('missing trigger')
#
#         stimuli = []
#
#         stimuli.append(Pause(duration=pre_stim_pause))
#         stimuli.append(FullFieldPainterStimulus(duration=duration_sec-shock_duration,
#                                                 color=(255, 255, 255)))  # flash duration
#         stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
#                                      pulse_n=1, pulse_dur_ms=5))
#         stimuli.append(FullFieldPainterStimulus(duration=shock_duration, color=(255, 255, 255)))  # flash duration
#         stimuli.append(Pause(duration=period_sec - duration_sec - pre_stim_pause ))
#
#         super().__init__(*args, stimuli=stimuli, **kwargs)

#
# def make_value_blocks(duration_value_tuples):
#     """ For all the stimuli that accept a motion parameter,
#         we usually want one thing to stay the same in a block
#
#     :param duration_value_tuples:
#     :return:
#     """
#     t = []
#     vals = []
#
#     for dur, val in duration_value_tuples:
#         if len(t) == 0:
#             last_t = 0
#         else:
#             last_t = t[-1]
#
#         t.extend([last_t, last_t+dur])
#         vals.extend([val, val])
#     return t, vals


# class ReafferenceProtocol(Protocol):
#     name = 'reafference'
#     def __init__(self, *args, n_backwards=7, pause_duration=7, backwards_duration=0.5,
#                  forward_duration=4, backward_vel=20, forward_vel=10,
#                  n_forward=14, gain=1, grating_period=10, base_gain=10,
#                  fish_motion_estimator=None, **kwargs):
#
#         gains = []
#         vels = []
#         ts = []
#         last_t = 0
#         for i in range(n_backwards):
#             ts.extend([last_t, last_t+pause_duration,
#                        last_t + pause_duration, last_t+pause_duration+backwards_duration])
#             vels.extend([0, 0, -backward_vel, -backward_vel])
#             last_t = ts[-1]
#         gains.extend([0]*n_backwards*4)
#
#         for i in range(n_forward):
#
#             # blocks of two are in random order gain 0 or gain 1
#             if i % 2 == 0:
#                 gain_exists = bool(np.random.randint(0, 1))
#             else:
#                 gain_exists = not gain_exists
#
#             ts.extend([last_t, last_t+pause_duration,
#                        last_t + pause_duration, last_t+pause_duration+forward_duration])
#             vels.extend([0, 0, forward_vel, forward_vel])
#             gains.extend([0, 0, gain_exists*gain, gain_exists*gain])
#             last_t = ts[-1]
#
#         super().__init__(stimuli=[ClosedLoop1D_variable_motion(motion=pd.DataFrame(
#             dict(t=ts, base_vel=vels, gain=gains)), grating_period=grating_period,
#             shunting=True, base_gain=base_gain,
#             fish_motion_estimator=fish_motion_estimator)])

#
# class MultistimulusExp006Protocol(Protocol):
#     name = 'multiple stimuli exp006'
#     def __init__(self, *args,
#                  flash_durations=(0.05, 0.1, 0.2, 0.5, 1, 3),
#                  velocities=(3, 10, 30, -10),
#                  pre_stim_pause=4,
#                  one_stimulus_duration=7,
#                  grating_motion_duration=4,
#                  grating_args=None,
#                  shock_args=None,
#                  shock_on=False,
#                  water_on=True,
#                  lr_vel=10,
#          **kwargs):
#
#         if grating_args is None:
#             grating_args = dict()
#         if shock_args is None:
#             shock_args = dict()
#
#         stimuli = []
#         for flash_duration in flash_durations:
#             stimuli.append(FullFieldPainterStimulus(duration=flash_duration,
#                                                     color=(255, 0, 0)))  # flash duration
#             stimuli.append(Pause(duration=one_stimulus_duration-flash_duration))
#
#         t = [0, one_stimulus_duration]
#         y = [0., 0.]
#         x = [0., 0.]
#
#         for vel in velocities:
#             t.append(t[-1] + grating_motion_duration)
#             y.append(y[-1] + vel*grating_motion_duration)
#             t.append(t[-1] + one_stimulus_duration)
#             y.append(y[-1])
#             x.extend([0., 0.])
#
#         last_time = t[-1]
#         motion = pd.DataFrame(dict(t=t,
#                                    x=x,
#                                    y=y))
#         stimuli.append(MovingGratingStimulus(motion=motion,
#                                              duration=last_time,
#                                              **grating_args))
#
#         if lr_vel>0:
#             t = [0, one_stimulus_duration]
#             y = [0., 0.]
#             x = [0., 0.]
#             for xvel in [-lr_vel, lr_vel]:
#                 t.append(t[-1] + grating_motion_duration)
#                 x.append(x[-1] + xvel * grating_motion_duration)
#                 t.append(t[-1] + one_stimulus_duration)
#                 x.append(x[-1])
#                 y.extend([0., 0.])
#             last_time = t[-1]
#             motion = pd.DataFrame(dict(t=t,
#                                        x=x,
#                                        y=y))
#             grating_args_v = deepcopy(grating_args)
#             grating_args_v['grating_orientation'] = 'vertical'
#             stimuli.append(MovingGratingStimulus(motion=motion,
#                                                  **grating_args_v,
#                                                  duration=last_time))
#
#         if shock_on:
#             stimuli.append(Pause(duration=pre_stim_pause))
#             stimuli.append(ShockStimulus(**shock_args))
#             stimuli.append(Pause(duration=one_stimulus_duration))
#
#         if water_on:
#             im_vel = 10
#             stimuli.append(Pause(duration=pre_stim_pause))
#             t = [0, one_stimulus_duration]
#             y = [0., 0.]
#             x = [0., 0.]
#
#             dxs = [-1, 1, 0, 0]
#             dys = [0, 0, 1, 1]
#             for dx, dy in zip(dxs, dys):
#                 t.append(t[-1] + grating_motion_duration)
#                 x.append(x[-1] + dx * im_vel * grating_motion_duration)
#                 y.append(y[-1] + dy * im_vel * grating_motion_duration)
#                 t.append(t[-1] + one_stimulus_duration)
#                 x.append(x[-1])
#                 y.append(y[-1])
#
#             last_time = t[-1]
#             motion = pd.DataFrame(dict(t=t,
#                                        x=x,
#                                        y=y))
#
#             stimuli.append(MovingBackgroundStimulus(motion=motion,
#                                                  duration=last_time,
#                             background=existing_file_background("/Users/vilimstich/PhD/j_sync/underwater/SeamlessRocks.png")))
#
#         super().__init__(*args, stimuli=stimuli, **kwargs)

class VRProtocol(Protocol):
    name = 'VR protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'background_image': 'underwater_caustics.jpg',
                                'n_motions': 5,
                                'moving_phase_duration': 10,
                                'angle_between_phases': 90,
                                'velocity': 10,
                                'pause_duration': 0}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        motion = []

        angle = 0
        t = 0
        for i in range(self.params['n_motions']):
            vx = np.cos(angle)*self.params['velocity']
            vy = np.sin(angle) * self.params['velocity']
            motion.append([t, vx, vy])
            motion.append([t + self.params['moving_phase_duration'], vx, vy])
            angle += self.params['angle_between_phases']
            t += self.params['moving_phase_duration']
            if self.params['pause_duration'] > 0:
                motion.append([t, 0, 0])
                motion.append(
                    [t + self.params['pause_duration'], 0, 0])
                t += self.params['pause_duration']

        motion = pd.DataFrame(motion, columns=['t', 'vel_x', 'vel_y'])
        stimuli = [
            VRMotionStimulus(background=self.params['background_image'],
                             motion=motion,
                             duration=motion.t.iat[-1])
        ]

        return stimuli