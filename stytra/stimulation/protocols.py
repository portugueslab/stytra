from stytra.stimulation.stimuli import Pause, \
    ShockStimulus, SeamlessGratingStimulus, VideoStimulus, \
    FullFieldPainterStimulus, ClosedLoop1D_variable_motion, MovingStimulus, \
    PartFieldStimulus, VRMotionStimulus, SeamlessImageStimulus
from stytra.stimulation.backgrounds import existing_file_background
from stytra.stimulation import Protocol
import pandas as pd
import numpy as np
from stytra.stimulation.backgrounds import gratings
import math
from itertools import product

from copy import deepcopy


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
    def __init__(self, *args, period_sec=5,  flash_duration=2, **kwargs):

        stimuli = []

        stimuli.append(Pause(duration=period_sec-flash_duration))
        stimuli.append(FullFieldPainterStimulus(duration=flash_duration,
                                                color=(255, 255, 255)))  # flash duration

        super().__init__(*args, stimuli=stimuli, **kwargs)


class ShockProtocol(Protocol):
    name = 'shock protocol'
    def __init__(self, repetitions=10, period_sec=30, pre_stim_pause=20.95,
                 prepare_pause=2, pyb=None):
        """

        :param repetitions:
        :param prepare_pause:
        :param pyb:
        :param zmq_trigger:
        """
        super().__init__()

        stimuli = []
       # pre-shock interval
        for i in range(repetitions):  # change here for number of trials
            stimuli.append(Pause(duration=pre_stim_pause))
            stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
                                         pulse_n=1, pulse_dur_ms=5))
            stimuli.append(Pause(duration=period_sec-pre_stim_pause))  # post flash interval

        self.stimuli = stimuli
        self.current_stimulus = stimuli[0]
        self.name = 'shock'


class FlashShockProtocol(Protocol):
    name = 'Flash and shock'
    def __init__(self, *args, period_sec=30, duration_sec=1, pre_stim_pause=20, shock_duration=0.05,
                 prepare_pause=2, pyb=None, zmq_trigger=None, **kwargs):
        """

        :param repetitions:
        :param prepare_pause:
        :param pyb:
        :param zmq_trigger:
        """
        if not zmq_trigger:
            print('missing trigger')

        stimuli = []

        stimuli.append(Pause(duration=pre_stim_pause))
        stimuli.append(FullFieldPainterStimulus(duration=duration_sec-shock_duration, color=(255, 255, 255)))  # flash duration
        stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
                                     pulse_n=1, pulse_dur_ms=5))
        stimuli.append(FullFieldPainterStimulus(duration=shock_duration, color=(255, 255, 255)))  # flash duration
        stimuli.append(Pause(duration=period_sec - duration_sec - pre_stim_pause ))

        super().__init__(*args, stimuli=stimuli, **kwargs)


def make_value_blocks(duration_value_tuples):
    """ For all the stimuli that accept a motion parameter,
        we usually want one thing to stay the same in a block

    :param duration_value_tuples:
    :return:
    """
    t = []
    vals = []

    for dur, val in duration_value_tuples:
        if len(t) == 0:
            last_t = 0
        else:
            last_t = t[-1]

        t.extend([last_t, last_t+dur])
        vals.extend([val, val])
    return t, vals


class ReafferenceProtocol(Protocol):
    name = 'reafference'
    def __init__(self, *args, n_backwards=7, pause_duration=7, backwards_duration=0.5,
                 forward_duration=4, backward_vel=20, forward_vel=10,
                 n_forward=14, gain=1, grating_period=10, base_gain=10,
                 fish_motion_estimator=None, **kwargs):

        gains = []
        vels = []
        ts = []
        last_t = 0
        for i in range(n_backwards):
            ts.extend([last_t, last_t+pause_duration,
                       last_t + pause_duration, last_t+pause_duration+backwards_duration])
            vels.extend([0, 0, -backward_vel, -backward_vel])
            last_t = ts[-1]
        gains.extend([0]*n_backwards*4)

        for i in range(n_forward):

            # blocks of two are in random order gain 0 or gain 1
            if i % 2 == 0:
                gain_exists = bool(np.random.randint(0, 1))
            else:
                gain_exists = not gain_exists

            ts.extend([last_t, last_t+pause_duration,
                       last_t + pause_duration, last_t+pause_duration+forward_duration])
            vels.extend([0, 0, forward_vel, forward_vel])
            gains.extend([0, 0, gain_exists*gain, gain_exists*gain])
            last_t = ts[-1]

        super().__init__(stimuli=[ClosedLoop1D_variable_motion(motion=pd.DataFrame(
            dict(t=ts, base_vel=vels, gain=gains)), grating_period=grating_period,
            shunting=True, base_gain=base_gain,
            fish_motion_estimator=fish_motion_estimator)])


class MultistimulusExp06Protocol(Protocol):
    name = 'multiple stimuli exp006'
    def __init__(self, *args,
                 flash_durations=(0.05, 0.1, 0.2, 0.5, 1, 3),
                 velocities=(3, 10, 30, -10),
                 pre_stim_pause=4,
                 one_stimulus_duration=7,
                 grating_motion_duration=4,
                 grating_args=None,
                 shock_args=None,
                 shock_on=False,
                 water_on=True,
                 lr_vel=10,
         **kwargs):

        if grating_args is None:
            grating_args = dict()
        if shock_args is None:
            shock_args = dict()

        stimuli = []
        for flash_duration in flash_durations:
            stimuli.append(FullFieldPainterStimulus(duration=flash_duration,
                                                    color=(255, 0, 0)))  # flash duration
            stimuli.append(Pause(duration=one_stimulus_duration-flash_duration))

        t = [0, one_stimulus_duration]
        y = [0., 0.]
        x = [0., 0.]

        for vel in velocities:
            t.append(t[-1] + grating_motion_duration)
            y.append(y[-1] + vel*grating_motion_duration)
            t.append(t[-1] + one_stimulus_duration)
            y.append(y[-1])
            x.extend([0., 0.])

        last_time = t[-1]
        motion = pd.DataFrame(dict(t=t,
                             x=x,
                             y=y))
        stimuli.append(MovingGratingStimulus(motion=motion,
                                           duration=last_time,
                                             **grating_args))

        if lr_vel>0:
            t = [0, one_stimulus_duration]
            y = [0., 0.]
            x = [0., 0.]
            for xvel in [-lr_vel, lr_vel]:
                t.append(t[-1] + grating_motion_duration)
                x.append(x[-1] + xvel * grating_motion_duration)
                t.append(t[-1] + one_stimulus_duration)
                x.append(x[-1])
                y.extend([0., 0.])
            last_time = t[-1]
            motion = pd.DataFrame(dict(t=t,
                                       x=x,
                                       y=y))
            grating_args_v = deepcopy(grating_args)
            grating_args_v['grating_orientation'] = 'vertical'
            stimuli.append(MovingGratingStimulus(motion=motion,
                                          **grating_args_v,
                                          duration=last_time))

        if shock_on:
            stimuli.append(Pause(duration=pre_stim_pause))
            stimuli.append(ShockStimulus(**shock_args))
            stimuli.append(Pause(duration=one_stimulus_duration))

        if water_on:
            im_vel = 10
            stimuli.append(Pause(duration=pre_stim_pause))
            t = [0, one_stimulus_duration]
            y = [0., 0.]
            x = [0., 0.]

            dxs = [-1, 1, 0, 0]
            dys = [0, 0, 1, 1]
            for dx, dy in zip(dxs, dys):
                t.append(t[-1] + grating_motion_duration)
                x.append(x[-1] + dx * im_vel * grating_motion_duration)
                y.append(y[-1] + dy * im_vel * grating_motion_duration)
                t.append(t[-1] + one_stimulus_duration)
                x.append(x[-1])
                y.append(y[-1])

            last_time = t[-1]
            motion = pd.DataFrame(dict(t=t,
                                       x=x,
                                       y=y))

            stimuli.append(MovingBackgroundStimulus(motion=motion,
                                                 duration=last_time,
                            background=existing_file_background("/Users/vilimstich/PhD/j_sync/underwater/SeamlessRocks.png")))

        super().__init__(*args, stimuli=stimuli, **kwargs)


class VisualCodingProtocol(Protocol):
    name = "visual coding protocol"
    def __init__(self, *args,
                 video_file=r"3minUnderwater.mp4",
                 n_directions=8,
                 n_split=4, #4
                 grating_period = 10,
                 grating_vel = 10,
                 part_field_duration=1,
                 part_field_pause=1,
                 inter_segment_pause=2,
                 grating_move_duration=5,
                 grating_pause_duration=2,
                 **kwargs):

        stimuli = []

        n_split = n_split

        for (ix, iy) in product(range(n_split), repeat=2):
            stimuli.append(PartFieldStimulus(
                bounding_box=(
                    ix/n_split,
                    iy/n_split,
                    1/n_split,
                    1/n_split),
                duration=part_field_duration))
            stimuli.append(Pause(duration=part_field_pause))

        stimuli.append(Pause(duration=inter_segment_pause))

        delta_theta = np.pi*2/n_directions

        grating_motion = pd.DataFrame(dict(t=[0,
             grating_pause_duration,
             grating_pause_duration+grating_move_duration,
             grating_pause_duration*2+grating_move_duration],
                                           x=[0,
                                               0,
                                               grating_move_duration*grating_vel,
                                               grating_move_duration*grating_vel]))
        moving_grating_class = type('MovingGratings',
                                    (MovingStimulus, SeamlessGratingStimulus),
                                    dict(name='moving_gratings'))
        for i_dir in range(n_directions):
            stimuli.append(moving_grating_class(duration=float(grating_motion.t.iat[-1]),
                                                motion=grating_motion,
                                                grating_period=grating_period,
                                 grating_angle=i_dir*delta_theta
                                 ))

        stimuli.append(Pause(duration=inter_segment_pause))

        stimuli.append(VideoStimulus(video_path=video_file, duration=180))
        super().__init__(*args, stimuli=stimuli, **kwargs)


class VRProtocol(Protocol):
    name='VR protocol'

    # For fish

    def __init__(self, *args, background_images=('checkerboard.jpg',
            'SeamlessRocks.jpg',

                                                 'underwater_caustics.jpg'),
                 n_velocities=200,
                 initial_angle=0,
                 delta_angle_mean=np.pi/6,
                 delta_angle_std =np.pi/6,
                 velocity_duration=15,
                 velocity_mean=7,
                 velocity_std=2,
                 **kwargs):
        full_t = 0
        motion = []
        dt = velocity_duration
        angle = initial_angle
        for i in range(n_velocities):
            angle += np.random.randn(1)[0]*delta_angle_std

            vel = np.maximum(np.random.randn(1)*velocity_std+velocity_mean, 0)[0]
            vy = np.sin(angle)*vel
            vx = np.cos(angle)*vel

            motion.append([full_t, vx, vy])
            motion.append([full_t+dt, vx, vy])
            full_t += dt

        motion = pd.DataFrame(motion, columns=['t', 'vel_x', 'vel_y'])
        print(motion)

        stimuli = [
            VRMotionStimulus(background=bgim, motion=motion,
                             duration=full_t)
            for bgim in background_images
        ]
        super().__init__(*args, stimuli=stimuli, **kwargs)