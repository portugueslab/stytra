from stytra.stimulation.stimuli import Pause, Flash, StartAquisition,\
    StopAquisition, PrepareAquisition, ShockStimulus, MovingSeamless, FullFieldPainterStimulus
from stytra.stimulation import Protocol
import pandas as pd
import numpy as np
from stytra.stimulation.backgrounds import gratings

import zmq


class LightsheetProtocol(Protocol):
    """ Protocols which run on the lightsheet have extra parameters

    """
    def __init__(self, *args, wait_for_lightsheet=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)

        self.current_stimulus = self.stimuli[0]
        self.lightsheet_config = dict()
        self.wait_for_lightsheet = wait_for_lightsheet

    def start(self):
        # Start only when received the GO signal from the lightsheet
        if self.wait_for_lightsheet:
            self.zmq_socket.bind("tcp://*:5555")
            print('bound socket')
            self.lightsheet_config = self.zmq_socket.recv_json()
            print('received config')
            # send the duration of the protocol so that
            # the scanning can stop
            self.zmq_socket.send_json(self.duration)
        super().start()



# Spontaneus activity
class SpontActivityProtocol(LightsheetProtocol):
    # TODO @Luigi inherit from LightsheetProtocol
    def __init__(self, duration_sec=60):
        """
        :param duration:
        :param prepare_pause:
        :param zmq_trigger:
        """


        stimuli = []
        stimuli.append(Pause(duration=duration_sec))  # change here for duration (in s)

        self.stimuli = stimuli
        self.current_stimulus = stimuli[0]
        super().__init__(stimuli=stimuli, name='spontaneous')


class FlashProtocol(Protocol):
    def __init__(self, repetitions=10, period_sec=30, duration_sec=1, pre_stim_pause=20,
                 prepare_pause=2, zmq_trigger=None):
        """
        :param repetitions:
        :param prepare_pause:
        :param zmq_trigger:
        """
        super().__init__()
        if not zmq_trigger:
            print('missing trigger')

        stimuli = []
        stimuli.append(Pause(duration=1))
        stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
        stimuli.append(Pause(duration=prepare_pause))
        stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start acquisition
        # stimuli.append(Pause(duration=period_sec-duration_sec))  # pre-flash interval
        for i in range(repetitions):
            stimuli.append(Pause(duration=pre_stim_pause))
            stimuli.append(Flash(duration=1, color=(255, 255, 255)))  # flash duration
            stimuli.append(Pause(duration=period_sec-duration_sec-pre_stim_pause))  # post flash interval

        self.stimuli = stimuli
        self.current_stimulus = stimuli[0]
        self.name = 'flash'


class ShockProtocol(Protocol):
    def __init__(self, repetitions=10, period_sec=30, pre_stim_pause=20.95,
                 prepare_pause=2, pyb=None, zmq_trigger=None):
        """

        :param repetitions:
        :param prepare_pause:
        :param pyb:
        :param zmq_trigger:
        """
        super().__init__()
        if not zmq_trigger:
            print('missing trigger')

        stimuli = []
        stimuli.append(Pause(duration=1))
        stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
        stimuli.append(Pause(duration=prepare_pause))
        stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition
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
    def __init__(self, repetitions=10, period_sec=30, duration_sec=1, pre_stim_pause=20, shock_duration=0.05,
                 prepare_pause=2, pyb=None, zmq_trigger=None):
        """

        :param repetitions:
        :param prepare_pause:
        :param pyb:
        :param zmq_trigger:
        """
        super().__init__()
        if not zmq_trigger:
            print('missing trigger')

        stimuli = []
        stimuli.append(Pause(duration=1))
        stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
        stimuli.append(Pause(duration=prepare_pause))
        stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition

        for i in range(repetitions):  # change here for number of pairing trials
            stimuli.append(Pause(duration=pre_stim_pause))
            stimuli.append(Flash(duration=duration_sec-shock_duration, color=(255, 255, 255)))  # flash duration
            stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
                                         pulse_n=1, pulse_dur_ms=5))
            stimuli.append(Flash(duration=shock_duration, color=(255, 255, 255)))  # flash duration
            stimuli.append(Pause(duration=period_sec - duration_sec - pre_stim_pause ))

        self.stimuli = stimuli
        self.current_stimulus = stimuli[0]
        self.name = 'flashshock'


class MultistimulusExp06Protocol(LightsheetProtocol):
    def __init__(self, repetitions=20,
                        flash_durations=(0.05, 0.1, 0.2, 0.5, 1, 3),
                        velocities=(3, 10, 30, -10),
                        pre_stim_pause=4,
                        one_stimulus_duration=7,
                        grating_motion_duration=4,
                        grating_args=None,
                        shock_args=None,
                        mm_px=1,
                *args, **kwargs):

        if grating_args is None:
            grating_args = dict()
        if shock_args is None:
            shock_args = dict()

        grating_args['mm_px'] = mm_px
        stimuli = []
        for i in range(repetitions):  # change here for number of pairing trials
            stimuli.append(Pause(duration=pre_stim_pause))
            for flash_duration in flash_durations:
                stimuli.append(FullFieldPainterStimulus(duration=flash_duration, color=(255, 0, 0)))  # flash duration
                stimuli.append(Pause(duration=one_stimulus_duration-flash_duration))

            t = [0, one_stimulus_duration]
            y = [0., 0.]

            for vel in velocities:
                t.append(t[-1] + grating_motion_duration)
                y.append(y[-1] + vel*grating_motion_duration/mm_px)
                t.append(t[-1] + one_stimulus_duration)
                y.append(y[-1])

            last_time = t[-1]
            motion = pd.DataFrame(dict(t=t,
                                 x=np.zeros(len(y)),
                                 y=y))
            stimuli.append(MovingSeamless(motion=motion,
                                               background=gratings(**grating_args),
                                               duration=last_time))

            stimuli.append(Pause(duration=pre_stim_pause))
            stimuli.append(ShockStimulus(**shock_args))
            stimuli.append(Pause(duration=one_stimulus_duration))

        super().__init__(*args, stimuli=stimuli, **kwargs)
        self.name = 'exp006multistim'