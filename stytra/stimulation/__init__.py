from PyQt5.QtCore import pyqtSignal, QTimer, QObject
import datetime

from builtins import print

from stytra.stimulation.stimuli import DynamicStimulus


class Protocol(QObject):
    """ Class that manages the stimulation protocol, includes a timer,
    updating signals etc.

    """

    sig_timestep = pyqtSignal(int)
    sig_stim_change = pyqtSignal(int)
    sig_protocol_started = pyqtSignal()
    sig_protocol_finished = pyqtSignal()

    def __init__(self, stimuli=None, dt=1/60, log_print=True):
        """
        :param stimuli: list of stimuli for the protocol (list of Stimulus objects)
        :param dt: frame duration (sec)
        """
        super().__init__()

        self.t_start = None
        self.t = 0
        if stimuli:
            self.stimuli = stimuli
            self.current_stimulus = stimuli[0]
        self.i_current_stimulus = 0
        self.timer = QTimer()
        self.dt = dt

        # Log will be a list of stimuli states
        self.log = []
        self.log_print = log_print

    def start(self):
        self.t_start = datetime.datetime.now()
        self.timer.timeout.connect(self.timestep)
        self.timer.setSingleShot(False)
        self.timer.start(self.dt)
        self.current_stimulus.started = datetime.datetime.now()
        self.sig_protocol_started.emit()
        # self.sig_stim_change.emit(0) - not sure about commenting out this

    def timestep(self):
        self.t = (datetime.datetime.now() - self.t_start).total_seconds()  # Time from start in seconds
        self.current_stimulus.elapsed = (datetime.datetime.now() -
                                         self.current_stimulus.started).total_seconds()

        if self.current_stimulus.elapsed > self.current_stimulus.duration:  # If stimulus time is over
            self.sig_stim_change.emit(self.i_current_stimulus)
            self.update_log()

            if self.i_current_stimulus >= len(self.stimuli) - 1:
                self.end()
            else:
                self.i_current_stimulus += 1
                self.current_stimulus = self.stimuli[self.i_current_stimulus]
                self.current_stimulus.started = datetime.datetime.now()
                self.current_stimulus.start()

        self.sig_timestep.emit(self.i_current_stimulus)
        if isinstance(self.current_stimulus, DynamicStimulus):
            self.sig_stim_change.emit(self.i_current_stimulus)

    def end(self):
        self.sig_protocol_finished.emit()
        self.timer.timeout.disconnect()
        self.timer.stop()
        self.reset_log()

    def update_log(self):
        """This is coming directly from the Logger class and can be made better"""
        # Update with the data of the current stimulus:
        current_stim_dict = self.current_stimulus.get_state()
        new_dict = dict(current_stim_dict,
                             t_start=self.t - self.current_stimulus.elapsed, t_stop=self.t)
        if self.log_print:
            print(new_dict)
        self.log.append(new_dict)

    def reset_log(self):
        self.t_start = None
        self.t = 0
        for stimulus in self.stimuli:
            stimulus._started = None
            stimulus.elapsed = 0.0

        self.i_current_stimulus = 0
        self.current_stimulus = self.stimuli[0]
        self.timer = QTimer()

        # Log will be a list of stimuli states
        self.log = []

    def print(self):
        string = ''
        for stim in self.stimuli:
            string += '-' + stim.name

        print(string)



