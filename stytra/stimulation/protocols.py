from stytra.stimulation.stimuli import *
# , ClosedLoop1D_variable_motion,
from stytra.stimulation.backgrounds import existing_file_background
import pandas as pd
import numpy as np
from stytra.data_log import HasPyQtGraphParams
from random import shuffle, sample
from stytra.stimulation.backgrounds import gratings
from itertools import product

from copy import deepcopy


class Protocol(HasPyQtGraphParams):
    """ The Protocol class is thought as an easily subclassable class that
     generate a list of stimuli according to some parameterization.
     It basically constitutes a way of keeping together:
      - the parameters that describe the protocol
      - the function to generate the list of stimuli.

     The function get_stimulus_list is the core of the class: it is called
     by the ProtocolRunner and it generates a list with the stimuli that
     have to be used in the protocol. Everything else concerning e.g.
     calibration, or asset directories that have to be passed to the
     stimulus, is handled in the ProtocolRunner class to leave this class
     as light as possible.
     """

    name = ''

    def __init__(self):
        """Add standard parameters common to all kind of protocols.
        """
        super().__init__(name='stimulus_protocol_params')

        # Pre- and post- pause will be periods with a Pause stimulus before
        # and after the entire sequence of n repetitions of the stimulus.
        standard_params_dict = {'name': self.name,
                                'n_repeats': 1,
                                'pre_pause': 0.,
                                'post_pause': 0.}

        for child in self.params.children():
            self.params.removeChild(child)

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stimulus_list(self):
        """ Generate protocol from specified parameters. Called by the
        ProtocolRunner class where the Protocol instance is defined.
        This function puts together the stimulus sequence defined by each
        child class with the initial and final pause and repeats it the
        specified number of times. It should not change in subclasses.
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
        """ To be specified in each child class to return the proper list of
        stimuli.
        """
        return [Pause()]


class NoStimulation(Protocol):
    """ A void protocol.
    """
    name = 'no stimulation'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'duration': 5}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        stimuli = []

        stimuli.append(Pause(duration=self.params['duration']))

        return stimuli


class FlashProtocol(Protocol):
    name = 'flash protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'period_sec': 5.,
                                'flash_duration': 2., #,
                                'pino': 3}

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)

    def get_stim_sequence(self):
        stimuli = []

        stimuli.append(Pause(duration=self.params['period_sec'] - \
                                      3))  # self.params['flash_duration']))
        stimuli.append(FullFieldPainterStimulus(duration=5, # self.params['flash_duration'],
                                                color=(255, 255, 255)))

        return stimuli


class ShockProtocol(Protocol):
    name = 'shock protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'period_sec': 5.,
                                'flash_duration': 2.}

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)

    def get_stim_sequence(self):
        stimuli = []

        stimuli.append(Pause(duration=self.params['period_sec'] - \
                                      self.params['flash_duration']))
        stimuli.append(ShockStimulus())

        return stimuli


class OKRstim(Protocol):
    name = "OKR protocol"

    def __init__(self):
        super().__init__()

        params_dict = {'windmill_amplitude': np.pi/4,
                       'windmill_duration': 2.,
                       'windmill_arms': 12,
                       'inter_stim_pause': 5.,
                       'inter_rot_pause': 1.,
                       'internal_reps': 20,
                       'rotate': False}

        for key in params_dict:
            self.set_new_param(key, params_dict[key])

    def get_stim_sequence(self):
        stimuli = []

        stim_color = (255, 0, 0)
        p = self.params['inter_stim_pause']
        p2 = self.params['inter_rot_pause']
        windmill_freq = 1 / (self.params['windmill_duration'] * 2)

        STEP = 0.005
        osc_time_vect = np.arange(0, self.params['windmill_duration'] + STEP,
                                  STEP)

        stimlist = ['FCLW', 'FCCW', 'FCLW', 'FCCW'] #, 'RCLW', 'RCCW', 'LCLW', 'LCCW'] #,  'FCW2'] #, 'FCCW2', 'RCW2', 'RCCW2', 'LCW2', 'LCCW2']
        stimlistR = ['RCLW', 'RCCW']
        stimlistL = ['LCLW', 'LCCW']
        reps = self.params['internal_reps']
        stimlist.extend(stimlist * (reps - 1))
        # shuffle(stimlist)
        stimlistR.extend(stimlistR * (reps - 1))
        # shuffle(stimlistR)
        stimlistL.extend(stimlistL * (reps - 1))
        # shuffle(stimlistL)

        lrlist = [stimlistR, stimlistL]
        shuffle(lrlist)
        for l in lrlist:
            stimlist.extend(l)
        print(stimlist)
        # self.params['stim_seq'] = self.stimlist

        for stim in stimlist:
            theta_vect_clw = np.cos(
                osc_time_vect * 2 * np.pi * windmill_freq) * \
                            self.params['windmill_amplitude'] / 2 - \
                            self.params['windmill_amplitude'] / 2

            # Initial pause:
            t = [0, p / 2]
            theta = [0, 0]

            # First half rotation:
            t.extend(t[-1] + osc_time_vect)
            theta.extend(theta_vect_clw)

            # Second pause:
            t.extend([t[-1] + p2])
            theta.extend([theta[-1]])

            # Rotation back:
            t.extend(t[-1] + osc_time_vect)
            theta.extend(theta[-1] - theta_vect_clw)

            # Final pause:
            t.extend([t[-1] + p / 2])
            theta.extend([theta[-1]])

            if 'CLW' in stim:
                theta = -np.array(theta)

            mov_dict = pd.DataFrame(dict(t=t, theta=theta))

            b = 0.1  # factor specifying endpoints of clip mask from center
            # Set clip rectangle to full field or left/right hemi-field:
            if stim[0] == 'F':
                clip_rect = None
            elif stim[0] == 'L':
                clip_rect = [(0, b), (0.5, 0.5), (0, 1-b)]
            elif stim[0] == 'R':
                clip_rect = [(1, b), (0.5, 0.5), (1, 1-b)]

            # If rotation is required, swap x and y coords of clip masks:
            if self.params['rotate'] and clip_rect is not None:
                for j, i in enumerate(clip_rect):
                    clip_rect[j] = (i[1], i[0])

            stimuli.append(SeamlessWindmillStimulus(motion=mov_dict,
                                                    n_arms=self.params[
                                                            'windmill_arms'],
                                                    color=stim_color,
                                                    clip_rect=clip_rect))

        return stimuli


class ContinuousOKRstim(Protocol):
    name = "OKR continuous protocol"

    def __init__(self):
        super().__init__()

        params_dict = {'windmill_amplitude': np.pi/4,
                       'windmill_duration': 2.,
                       'windmill_arms': 12,
                       'inter_stim_pause': 0.,
                       'rotate': False,
                       'field': 'F',
                       'edge_1': 0.1,
                       'edge_2': 2,
                       'center_off': 0.1,
                       'internal_reps': 1}

        for key in params_dict:
            self.set_new_param(key, params_dict[key])

    def get_stim_sequence(self):
        stimuli = []

        stim_color = (255, 0, 0)
        p = self.params['inter_stim_pause']
        windmill_freq = 1 / (self.params['windmill_duration'] * 2)

        STEP = 0.005
        osc_time_vect = np.arange(0, self.params['windmill_duration'] + STEP,
                                  STEP)

        theta_vect_clw = np.cos(osc_time_vect * 2 * np.pi * windmill_freq) * \
            self.params['windmill_amplitude'] / 2 - \
            self.params['windmill_amplitude'] / 2

        # Initial pause:
        t = [0, p / 2]
        theta = [0, 0]

        # First half rotation:
        t.extend(t[-1] + osc_time_vect)
        theta.extend(theta_vect_clw)

        # Rotation back:
        t.extend(t[-1] + osc_time_vect)
        theta.extend(theta[-1] - theta_vect_clw)

        # Final pause:
        t.extend([t[-1] + p / 2])
        theta.extend([theta[-1]])

        mov_dict = pd.DataFrame(dict(t=t, theta=theta))

        b_1 = self.params['edge_1']  # factor specifying endpoints of clip mask from center
        b_2 = self.params['edge_2']
        c = self.params['center_off']

        # Set clip rectangle to full field or left/right hemi-field:
        if self.params['field'] == 'F':
            clip_rect = None
        elif self.params['field'] == 'L':
            clip_rect = [(0, b_1), (0.5 - c, 0.5), (0, 1-b_2)]
        elif self.params['field'] == 'R':
            clip_rect = [(1, b_1), (0.5 + c, 0.5), (1, 1-b_2)]

        # If rotation is required, swap x and y coords of clip masks:
        if self.params['rotate'] and clip_rect is not None:
            for j, i in enumerate(clip_rect):
                clip_rect[j] = (i[1], i[0])

        for i in self.params['internal_reps']:
            stimuli.append(SeamlessWindmillStimulus(motion=mov_dict,
                                                    n_arms=self.params[
                                                            'windmill_arms'],
                                                    color=stim_color,
                                                    clip_rect=clip_rect))

        return stimuli


# class ContinuousDoubleOKRstim(Protocol):
#     name = "OKR continuous double protocol"
#
#     def __init__(self):
#         super().__init__()
#
#         params_dict = {'windmill_amplitude': np.pi/4,
#                        'windmill_duration': 2.,
#                        'windmill_arms': 8,
#                        'inter_stim_pause': 0.,
#                        'rotate': False,
#                        'field': 'L',
#                        'edge_1': 10,
#                        'edge_2': 10,
#                        'center_off': 0.}
#
#         for key in params_dict:
#             self.set_new_param(key, params_dict[key])
#
#     def get_stim_sequence(self):
#         stimuli = []
#
#         stim_color = (255, 0, 0)
#         p = self.params['inter_stim_pause']
#         windmill_freq = 1 / (self.params['windmill_duration'] * 2)
#
#         STEP = 0.005
#         osc_time_vect = np.arange(0, self.params['windmill_duration'] + STEP,
#                                   STEP)
#
#         theta_vect_clw = np.cos(osc_time_vect * 2 * np.pi * windmill_freq) * \
#                         self.params['windmill_amplitude'] / 2 - \
#                         self.params['windmill_amplitude'] / 2
#
#         # Initial pause:
#         t = [0, p / 2]
#         theta = [0, 0]
#
#         # First half rotation:
#         t.extend(t[-1] + osc_time_vect)
#         theta.extend(theta_vect_clw)
#
#         # Rotation back:
#         t.extend(t[-1] + osc_time_vect)
#         theta.extend(theta[-1] - theta_vect_clw)
#
#         # Final pause:
#         t.extend([t[-1] + p / 2])
#         theta.extend([theta[-1]])
#
#         mov_dict = pd.DataFrame(dict(t=t, theta=theta))
#         mov_dict_still = pd.DataFrame(dict(t=[t[0], t[-1]],
#                                            theta=theta[:1]*2))
#
#         # factor specifying endpoints of clip mask from center
#         b_1 = self.params['edge_1']
#         b_2 = self.params['edge_2']
#         c = self.params['center_off']
#
#         # Set clip rectangle to full field or left/right hemi-field:
#         clip_rect_l = [(0, b_1), (0.5 - c, 0.5), (0, 1-b_2)]
#         clip_rect_r = [(1, b_1), (0.5 + c, 0.5), (1, 1-b_2)]
#
#         # If rotation is required, swap x and y coords of clip masks:
#         if self.params['rotate']:
#             for clip_rect in [clip_rect_l, clip_rect_r]:
#                 for j, i in enumerate(clip_rect):
#                     clip_rect[j] = (i[1], i[0])
#
#         if self.params['field'] == 'L':
#             left_dict = mov_dict
#             right_dict = mov_dict_still
#         else:
#             right_dict = mov_dict
#             left_dict = mov_dict_still
#
#         windmill_l = SeamlessWindmillStimulus(motion=left_dict,
#                                               n_arms=self.params[
#                                                         'windmill_arms'],
#                                               color=stim_color)
#         windmill_r = SeamlessWindmillStimulus(motion=right_dict,
#                                               n_arms=self.params[
#                                                      'windmill_arms'],
#                                               color=stim_color)
#
#         stimuli.append(PainterStimulusCombiner([windmill_r, windmill_l]))#,
#                                               #  windmill_r]))
#
#         return stimuli


class Exp022ImagingProtocol(Protocol):
    name = "exp022 imaging protocol"

    def __init__(self):
        super().__init__()

        params_dict = {'initial_pause': 0.,
                       'windmill_amplitude': np.pi * 0.444,
                       'windmill_duration': 10.,
                       'windmill_arms': 8,
                       'windmill_freq': 0.1,
                       'inter_stim_pause': 10.,
                       'grating_cycle': 10,
                       'grating_vel': 10.,
                       'grating_duration': 10.,
                       'flash_duration': 2}

        for key in params_dict:
            self.set_new_param(key, params_dict[key])

    def get_stim_sequence(self):
        stimuli = []


        # # initial dark field
        stimuli.append(Pause(duration=self.params['initial_pause']))
        stim_color = (255, 0, 0)
        #
        # # gratings
        p = self.params['inter_stim_pause']
        v = self.params['grating_vel']
        d = self.params['grating_duration']

        # tuple for x, t, theta

        vel_tuple = [(0, 0, np.pi/2),
                     (p, 0, np.pi/2),
                     (d, -0.3*v, np.pi/2),  # slow
                     (p, 0, np.pi/2),
                     (d, -v, np.pi/2),  # medium
                     (p, 0, np.pi / 2),
                     (d, -3*v, np.pi / 2),  # fast
                     (p, 0, np.pi/2),
                     (d, v, np.pi/2),  # backward
                     (p/2, 0, np.pi/2),
                     (0,0,0),   # set the grating to horizontal
                     (p/2, 0, 0),
                     (d, v, 0),  # leftwards
                     (p, 0, 0),
                     (d, -v, 0),
                     (p/2, 0, 0)]  # rightwards

        t = [0]
        x = [0]
        theta = [0]

        for dt, vel, th in vel_tuple:
            t.append(t[-1] + dt)
            x.append(x[-1] + dt * vel)
            theta.append(th)

        stimuli.append(SeamlessGratingStimulus(motion=pd.DataFrame(dict(t=t,
                                                                        x=x,
                                                                        theta=theta)),
                                               grating_period=self.params[
                                                   'grating_cycle'],
                                               color=stim_color))
        # windmill for OKR

        STEP = 0.005

        osc_time_vect = np.arange(0, self.params['windmill_duration'] + STEP,
                                  STEP)
        theta_vect_cw = np.cos(
            osc_time_vect * 2 * np.pi * self.params['windmill_freq']) * \
                        self.params['windmill_amplitude'] / 2

        # Initial pause:
        t = [0, p / 2]
        theta = [self.params['windmill_amplitude'] / 2, ] * 2  # initial pause

        # CW starting OKR:
        t.extend(t[-1] + osc_time_vect[:int(len(osc_time_vect) / 2)])
        theta.extend(theta_vect_cw[:int(len(theta_vect_cw) / 2)])

        # pause in the middle
        t.extend([t[-1] + p])
        theta.extend([theta[-1]])

        # finishing CW rotation
        t.extend(t[-1] + osc_time_vect[:int(len(osc_time_vect) / 2)])
        theta.extend(theta_vect_cw[int(len(theta_vect_cw) / 2):])

        # Final pause:
        t.extend([t[-1] + p / 2])
        theta.extend([theta[-1]])

        # OKR: whole field, left and right:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                         theta=theta)),
                                                n_arms=self.params[
                                                    'windmill_arms'],
                                                color=stim_color))

        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                         theta=theta)),
                                                n_arms=self.params[
                                                    'windmill_arms'],
                                                color=stim_color,
                                                clip_rect=[(0, -0.25),
                                                           (0.5, 0.5),
                                                           (0, 1.25)]))

        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                         theta=theta)),
                                                n_arms=self.params[
                                                    'windmill_arms'],
                                                color=stim_color,
                                                clip_rect=[(1, -0.25),
                                                           (0.5, 0.5),
                                                           (1, 1.25)]))

        stimuli.append(Pause(duration=p / 2))

        # ---------------
        # Final flashes:
        for i in range(4):
            stimuli.append(
                FullFieldPainterStimulus(duration=self.params['flash_duration'],
                                         color=(255, 0, 0)))  # flash duration
            stimuli.append(
                Pause(duration=self.params['flash_duration']))  # flash duration

        stimuli.append(Pause(duration=p - self.params['flash_duration']))
        return stimuli


class OMRProtocol(Protocol):
    name = "OMR  protocol"

    def __init__(self):
        super().__init__()

        params_dict = {'initial_pause': 0.,
                       'inter_stim_pause': 5.,
                       'grating_vel': 10.,
                       'grating_duration': 10.,
                       'grating_cycle': 10}

        for key in params_dict:
            self.set_new_param(key, params_dict[key])

    def get_stim_sequence(self):
        stimuli = []


        # # initial dark field
        stimuli.append(Pause(duration=self.params['initial_pause']))
        stim_color = (255, 0, 0)
        #
        # # gratings
        p = self.params['inter_stim_pause']
        v = self.params['grating_vel']
        d = self.params['grating_duration']

        # tuple for x, t, theta

        vel_tuple = [(0, 0, np.pi/2),
                     (p, 0, np.pi/2),
                     (d, -v, np.pi/2),  # slow
                     (p, 0, np.pi/2)]

        t = [0]
        x = [0]
        theta = [0]


        for dt, vel, th in vel_tuple:
            t.append(t[-1] + dt)
            x.append(x[-1] + dt * vel)
            theta.append(th)

        stimuli.append(SeamlessGratingStimulus(motion=pd.DataFrame(dict(t=t,
                                                                        x=x,
                                                                        theta=th)),
                                               grating_period=self.params[
                                                   'grating_cycle'],
                                               color=stim_color))
        return stimuli


class Exp014Protocol(Protocol):
    name = "exp014 protocol"

    def __init__(self):
        super().__init__()

        standard_params_dict = {'inter_stim_pause': 5.,
                                'grating_period': 10,
                                'grating_vel': 10,
                                'grating_duration': 10.,
                                'flash_duration': 1.}
        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        stimuli = list()

        # dark field

        stimuli.append(Pause(duration=self.params['inter_stim_pause']))
        stim_color = (255, 0, 0)

        # ---------------

        # ---------------
        # Gratings with three different velocities

        p = self.params['inter_stim_pause']
        s = self.params['grating_duration']
        v = self.params['grating_vel']
        theta = np.pi/2

        dt_vel_tuple = [(0, 0, theta),  # set grid orientation to horizontal
                        (p, 0, theta),
                        (s, -0.3 * v, theta),  # slow
                        (p, 0, theta),
                        (s, -v, theta),  # middle
                        (p, 0, theta),
                        (s, -3 * v, theta),  # fast
                        (p, 0, theta)]

        x = [0]
        t = [0]
        theta = [0]

        for dt, vel, th in dt_vel_tuple:
            t.append(t[-1] + dt)
            x.append(x[-1] + dt * vel)
            theta.append(th)

        stimuli.append(SeamlessGratingStimulus(
            motion=pd.DataFrame(dict(t=t,
                                     x=x,
                                     theta=theta)),
            grating_period=self.params[
               'grating_period'],
            color=stim_color))

        # ---------------
        # Final flashes:
        for i in range(4):
            stimuli.append(
                FullFieldPainterStimulus(duration=self.params['flash_duration'],
                                         color=(255, 0, 0)))  # flash duration
            stimuli.append(
                Pause(duration=self.params['flash_duration']))  # flash duration

        stimuli.append(Pause(duration=p - self.params['flash_duration']))
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
        # Static gratings and three different velocities are implemented with
        # a single grating stimulus whose positions are specified for having
        # the forward velocities:
        p = self.params['inter_stim_pause']
        s = self.params['grating_duration']
        v = self.params['grating_vel']
        # Grating tuple: t, x, theta
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
                        (p/2, 0, 0)]

        t = [0]
        x = [0]
        theta = [0]
        for dt, vel, th in dt_vel_tuple:
            t.append(t[-1] + dt)
            x.append(x[-1] + dt * vel)
            theta.append(th)


        stimuli.append(SeamlessGratingStimulus(motion=pd.DataFrame(dict(t=t,
                                                                        x=x,
                                                                        theta=theta)),
                                               grating_period=self.params['grating_period'],
                                               color=stim_color))

        # ---------------
        # Windmill for OKR

        # create velocity dataframe. Velocity is sinusoidal and starts from 0:
        STEP = 0.005
        osc_time_vect = np.arange(0, self.params['windmill_duration'] + STEP,
                                  STEP)
        # Initial pause:
        t = [0, p/2]
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
        # the offset avoid jumps in rotation
        theta.extend(theta[-1] + self.params['windmill_amplitude']/2 - \
            np.cos(osc_time_vect * 2 * np.pi * self.params['windmill_freq']) * \
                     self.params['windmill_amplitude']/2)

        # Final pause:
        t.extend([t[-1] + p/2])
        theta.extend([theta[-1]])  # initial pause


        # Full field OKR:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                         theta=theta)),
                                                n_arms=self.params['windmill_arms_n'],
                                                color=stim_color))
        # Half-field left OKR:

        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t, theta=theta)),
                                                n_arms=self.params['windmill_arms_n'],
                                                clip_rect=(0, 0, 0.5, 1),
                                                color=stim_color))
        # Half-field right OKR:
        stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                         theta=theta)),
                                                n_arms=self.params['windmill_arms_n'],
                                                clip_rect=(0.5, 0, 0.5, 1),
                                                color=stim_color))

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

        standard_params_dict = {'video_file': r"red.mp4",
                                'n_directions': 8,
                                'n_split': 4,
                                'grating_period': 10.,
                                'grating_vel': 10.,
                                'part_field_duration': 1.,
                                'part_field_pause': 2.,
                                'inter_segment_pause': 3.,
                                'grating_move_duration': 2.,
                                'grating_pause_duration': 2.,
                                'flash_size': 0.33}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        stimuli = []

        n_split = self.params['n_split']
        fieldsize = self.params['flash_size']
        start = (1-fieldsize)/2
        for (ix, iy) in product(range(n_split), repeat=2):
            stimuli.append(FullFieldPainterStimulus(
                clip_rect=(
                    start+ix*fieldsize / n_split,
                    start+iy*fieldsize / n_split,
                    fieldsize / n_split,
                    fieldsize / n_split),
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

        stimuli.append(VideoStimulus(video_path=self.params['video_file']))

        stimuli.append(Pause(duration=self.params['inter_segment_pause']))

        return stimuli


class MovingBackgroundProtocol(Protocol):
    name = 'moving backgound protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'background_images': 'underwater_caustics.jpg;checkerboard.jpg;SeamlessRocks.jpg',
                                'n_velocities': 200,
                                'velocity_duration': 15,
                                'initial_angle': 0,
                                'delta_angle_mean': np.pi/6,
                                'delta_angle_std': np.pi / 6,
                                'velocity': 10,
                                'velocity_mean': 7,
                                'velocity_std': 2,
                                'vr': False}

        for key in standard_params_dict.keys():
            self.set_new_param(key, standard_params_dict[key])

    def get_stim_sequence(self):
        full_t = 0
        motion = []
        dt = self.params['velocity_duration']
        angle = self.params['initial_angle']
        for i in range(self.params['n_velocities']):
            angle += np.random.randn(1)[0]*self.params['delta_angle_std']

            vel = np.maximum(np.random.randn(1)*self.params['velocity_std'] +
                             self.params['velocity_mean'], 0)[0]
            vy = np.sin(angle)*vel
            vx = np.cos(angle)*vel

            motion.append([full_t, vx, vy])
            motion.append([full_t+dt, vx, vy])
            full_t += dt

        motion = pd.DataFrame(motion, columns=['t', 'vel_x', 'vel_y'])

        if self.params["vr"]:
            cls = VRMotionStimulus
        else:
            cls = type('image_bg_stim', (SeamlessImageStimulus, MovingDynamicVel), dict())
            print("We are doing a seamless image stimulus")
        return [
            cls(background=bgim, motion=motion,
                duration=full_t)
            for bgim in self.params['background_images'].split(';')
        ]


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




class GratingsWindmillsProtocol(Protocol):

    name = 'Gratings windmills protocol'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'period_sec': 14.,
                                'shuffled_reps': 8,
                                'flash_duration': 7.}

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)

    def get_stim_sequence(self):
        temp_stimuli = []
        N_DIRECTIONS = 8
        PAUSE_DUR = 5
        STIM_DUR = 10
        GRATINGS_VEL = 10
        GRATINGS_PERIOD = 10
        OKR_VEL = (1/9)*(1/2)  # periods/sec
        N_REPS = self.params['shuffled_reps']
        # Gratings
        # Eight possible direction, constant vel of 10 mm/s
        # p = self.params['inter_stim_pause']
        # s = self.params['grating_duration']
        # v = self.params['grating_vel']
        # Grating tuple: t, x, theta

        temp_stimuli = many_directions_gratings(N_DIRECTIONS, PAUSE_DUR,
                                                STIM_DUR, GRATINGS_VEL,
                                                GRATINGS_PERIOD)

        # OKR base (numpy array to take negative later)
        final_pos = (OKR_VEL*STIM_DUR)*2*np.pi
        t = np.array([0, PAUSE_DUR, PAUSE_DUR+STIM_DUR, PAUSE_DUR*2+STIM_DUR])
        theta = np.array([0,  0, final_pos,  final_pos])

        # CW and CCW OKRs:
        temp_stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                              theta=theta)),
                                                     n_arms=9, color=[255, 0, 0]))
        temp_stimuli.append(SeamlessWindmillStimulus(motion=pd.DataFrame(dict(t=t,
                                                                              theta=-theta)),
                                                     n_arms=9, color=[255, 0, 0]))

        # Flash:
        flash = []
        flash.append(Pause(duration=PAUSE_DUR))
        flash.append(FullFieldPainterStimulus(duration=STIM_DUR,
                                     color=(255, 0, 0)))  # flash duration
        flash.append(Pause(duration=PAUSE_DUR))

        temp_stimuli.append(flash)

        # cumbersome but necessary for randomization preserving flash integrity:
        stim_full = []
        for n in range(N_REPS):
            stim_full += sample(temp_stimuli, len(temp_stimuli))

        stimuli = []
        for sublist in stim_full:
            try:
                for item in sublist:
                    stimuli.append(item)
            except TypeError:
                stimuli.append(sublist)

        return stimuli


class LuminanceRamp(Protocol):

    name = 'luminance ramps/steps'

    def __init__(self):
        super().__init__()

        standard_params_dict = {'shuffled_reps': 8}

        for key, value in standard_params_dict.items():
            self.set_new_param(key, value)

    def get_stim_sequence(self):
        stimuli = []

        l0 = 0  # luminance level 0
        l1 = 125  # luminance level 1
        l2 = 255  # luminance level 2
        p = 7  # period (fir both luminance length and pause length)
        n_reps = self.params['shuffled_reps']  # number of repetitions
        shuffle = True

        # Define individual stimuli intervals as
        # (duration, end luminance, "starts with step"*) *(1=yes, 0=no)
        double_step = [(p, l0, 1), (p, l1, 1), (p, l2, 1), (p, l1, 1)]
        full_step = [(p, l0, 1), (p, l2, 1)]
        long_step = [(p, l0, 1), (p*3, l2, 1)]
        ramp_step = [(p, l0, 1), (p*2, l2, 0), (p, l2, 0), (p*2, l0, 0)]

        stim = [double_step, full_step, long_step, ramp_step]

        stim_full = []
        for n in range(n_reps):
            if shuffle:
                stim_full += sample(stim, 4)
            else:
                stim_full += stim

        time = [0, ]
        lum = [l0, ]

        # Convert list of luminance steps and ramps into the DataFrame for the
        # stimulus class
        for stimulus in stim_full:
            for param in stimulus:
                if param[2] == 0:  # non-step
                    time.append(time[-1] + param[0])
                    lum.append(param[1])

                else:  # step
                    time.append(time[-1])
                    time.append(time[-1] + param[0])
                    lum.extend([param[1], param[1]])

        lum_df = pd.DataFrame(dict(t=np.asarray(time),
                                   lum=np.asarray(lum)))

        stimuli.append(DynamicFullFieldStimulus(lum_df=lum_df,
                                                color_0=(l0, )*3))
        stimuli.append(FullFieldPainterStimulus(duration=1,
                                                color=(l0, )*3))

        return stimuli


def many_directions_gratings(n_dirs, pause_len, gratings_len, gratings_vel,
                             grating_period):
    """ Function that create stimuli list of gratings moving in different
    directions.
    :param n_dirs:
    :param pause_len:
    :param gratings_len:
    :param gratings_vel:
    :return:
    """

    grat_mot = pd.DataFrame(dict(t=[0, pause_len,
                                    pause_len + gratings_len,
                                    pause_len * 2 + gratings_len],
                                 x=[0, 0,
                                    gratings_len * gratings_vel,
                                    gratings_len * gratings_vel]))

    delta_theta = np.pi * 2 / n_dirs

    stimuli = []
    for i_dir in range(n_dirs):
        stimuli.append(
            SeamlessGratingStimulus(duration=float(grat_mot.t.iat[-1]),
                                    motion=grat_mot,
                                    grating_period=grating_period,
                                    grating_angle=i_dir * delta_theta
                                    ))

    return stimuli

