from PyQt5.QtCore import pyqtSignal, QTimer
import datetime
from copy import deepcopy
import stimuli

class Protocol:
    """ Class that manages the stimulation protocol, includes a timer, updating
        signals etc.

    """

    sig_timestep = pyqtSignal()
    sig_stim_change = pyqtSignal()

    def __init__(self, stimuli, dt):
        self.t_start = None
        self.t = 0
        self.stimuli = deepcopy(stimuli)
        self.i_current_stimulus = 0
        self.current_stimulus = stimuli[0]
        self.timer = QTimer()
        self.dt = dt

    def start(self):
        self.t_start = datetime.datetime.now()
        self.protocol.finished = False
        self.timer.timeout.connect(self.protocol.time_step)
        self.timer.setSingleShot(False)
        self.timer.start(self.dt)

    def timestep(self):
        self.current_stimulus.elapsed = (datetime.datetime.now() - \
                                         self.current_stimulus.started).total_seconds()
        if self.current_stimulus.elapsed > self.current_stimulus.duration:
            if self.i_current_stimulus >= len(self.stimuli):
                self.end()
            else:
                self.i_current_stimulus += 1
                self.current_stimulus = self.stimuli[self.i_current_stimulus]
                self.current_stimulus.started = datetime.datetime.now()
        self.t = (datetime.datetime.now()-self.t_start).total_seconds()
        self.sig_timestep.emit()

    def end(self):
        self.timer.timeout.disconnect()
        self.timer.stop()
        self.logger.save()



