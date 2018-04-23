from PyQt5.QtCore import pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import QLayout, QPushButton, QWidget
from pyqtgraph.parametertree import ParameterTree
import datetime

from builtins import print
from copy import deepcopy

from stytra.stimulation.stimuli import DynamicStimulus, Pause
from stytra.collectors import Accumulator
from stytra.stimulation.protocols import FlashProtocol


class ProtocolRunner(QObject):
    """ Class that manages the stimulation protocol, includes a timer,
    updating signals etc.
    """

    sig_timestep = pyqtSignal(int)
    sig_stim_change = pyqtSignal(int)
    sig_protocol_started = pyqtSignal()
    sig_protocol_finished = pyqtSignal()
    sig_protocol_updated = pyqtSignal()  # parameters changed in the protocol

    def __init__(self, experiment=None, dt=1/60,
                 log_print=True, protocol=None):
        """ Constructor
        :param dt:
        :param log_print:
        :param experiment: the Experiment class where directory,
                           calibrator et similia will be found
        :param protocol:  protocol set instantiating the ProtocolRunner
        """
        super().__init__()

        self.experiment = experiment

        self.t_start = None
        self.t_end = None
        self.completed = False
        self.t = 0

        self.dt = dt
        self.timer = QTimer()

        self.protocol = None
        self.stimuli = []
        self.i_current_stimulus = None  # index of current stimulus
        self.current_stimulus = None  # current stimulus object
        self.past_stimuli_elapsed = None  # time elapsed in previous stimuli
        self.duration = None  # total duration of the protocol
        self.dynamic_log = None  # dynamic log for stimuli

        self.set_new_protocol(protocol)

        # Log will be a list of stimuli states:
        self.log = []
        self.log_print = log_print
        self.running = False

    def set_new_protocol(self, protocol_name):
        """ Set input protocol
        :param protocol: protocol name from the GUI
        """
        # If there was a protocol before, block params signal to avoid duplicate
        # call of the ProtocolRunner update_protocol function.
        # Otherwise it would be called by the change of the params three caused
        # by its deletion from the  _params called in the Protocol __init__().
        if protocol_name is not None:
            if self.protocol is not None:
                self.protocol.params.blockSignals(True)
            ProtocolClass = self.experiment.prot_class_dict[protocol_name]
            protocol = ProtocolClass()

            self.protocol = protocol

            self.update_protocol()

            # Connect changes to protocol parameters to update function:
            self.protocol.params.sigTreeStateChanged.connect(
                self.update_protocol)


            # Why were we resetting here?
            self.reset()

    def update_protocol(self):
        """ Update protocol (get a new stimulus list if protocol or parameters
        are changed).
        """
        self.stimuli = self.protocol.get_stimulus_list()

        self.current_stimulus = self.stimuli[0]

        # pass experiment to stimuli for calibrator and asset folders:
        for stimulus in self.stimuli:
            stimulus.initialise_external(self.experiment)

        self.dynamic_log = DynamicLog(self.stimuli)  # new stimulus log
        self.duration = self.get_duration()  # set new duration

        self.sig_protocol_updated.emit()

    def reset(self):
        """ Make the protocol ready to start again. Reset all ProtocolRunner
        and stimuli timers and elapsed times.
        """
        self.t_start = None
        self.t_end = None
        self.completed = False
        self.t = 0

        for stimulus in self.stimuli:
            stimulus._started = None
            stimulus._elapsed = 0.0

        self.i_current_stimulus = 0

        if len(self.stimuli) > 0:
            self.current_stimulus = self.stimuli[0]
        else:
            self.current_stimulus = None

    def start(self):
        """ Function for starting the protocol
        """
        self.t_start = datetime.datetime.now()  # get starting time
        self.timer.timeout.connect(self.timestep)  # connect timer to update fun
        self.timer.setSingleShot(False)
        self.timer.start()  # start the timer
        self.dynamic_log.starting_time = self.t_start  # save starting time
        self.dynamic_log.reset()  # reset the log
        self.log = []
        self.past_stimuli_elapsed = datetime.datetime.now()
        self.current_stimulus.started = datetime.datetime.now()
        self.sig_protocol_started.emit()
        self.running = True

    def timestep(self):
        """ Function called by QTimer timeout that update displayed stimulus
        :return:
        """
        if self.running:
            # Get total time from start in seconds:
            self.t = (datetime.datetime.now() - self.t_start).total_seconds()

            # Calculate elapsed time for current stimulus:
            self.current_stimulus._elapsed = (datetime.datetime.now() -
                                             self.past_stimuli_elapsed).total_seconds()

            # If stimulus time is over:
            if self.current_stimulus._elapsed > self.current_stimulus.duration:
                self.sig_stim_change.emit(self.i_current_stimulus)
                self.update_log()

                # Is this stimulus was also the last one end protocol:
                if self.i_current_stimulus >= len(self.stimuli) - 1:
                    self.completed = True
                    self.sig_protocol_finished.emit()

                else:
                    # Update the variable which keeps track when the last
                    # stimulus *should* have ended, in order to avoid
                    # drifting:

                    self.past_stimuli_elapsed += datetime.timedelta(
                        seconds=float(self.current_stimulus.duration))
                    self.i_current_stimulus += 1
                    self.current_stimulus = self.stimuli[self.i_current_stimulus]
                    self.current_stimulus.start()

            self.sig_timestep.emit(self.i_current_stimulus)

            # If stimulus is a constantly changing stimulus:
            if isinstance(self.current_stimulus, DynamicStimulus):
                self.sig_stim_change.emit(self.i_current_stimulus)
                self.current_stimulus.update()  # use stimulus update function
                self.update_dynamic_log()  # update dynamic log for stimulus

    def end(self):
        """ Called at the end of the protocol.
        """
        if not self.completed:  # if protocol was interrupted, update log anyway
            self.update_log()

        if self.running:
            self.running = False
            self.t_end = datetime.datetime.now()
            try:
                self.timer.timeout.disconnect()
                self.timer.stop()
            except: # TODO generic except
                pass

    def update_log(self):
        """ This is coming directly from the Logger class, can be made better.
        """
        # Update with the data of the current stimulus:
        current_stim_dict = self.current_stimulus.get_state()
        new_dict = dict(current_stim_dict,
                        t_start=self.t - self.current_stimulus._elapsed,
                        t_stop=self.t)
        # if self.log_print:
        #     print(new_dict)
        self.log.append(new_dict)

    def update_dynamic_log(self):
        if isinstance(self.current_stimulus, DynamicStimulus):
            self.dynamic_log.update_list((self.t,) + \
                self.current_stimulus.get_dynamic_state())

    def get_duration(self):
        """ Get total duration of the protocol.
        """
        total_duration = 0
        for stim in self.stimuli:
            total_duration += stim.duration
        return total_duration

    def print(self):
        """ Print protocol sequence.
        """
        string = ''
        for stim in self.stimuli:
            string += '-' + stim.name

        print(string)


# TODO maybe this should be defined elsewhere
class DynamicLog(Accumulator):
    def __init__(self, stimuli):
        super().__init__()
        # it is assumed the first dynamic stimulus has all the fields
        for stimulus in stimuli:
            if isinstance(stimulus, DynamicStimulus):
                self.header_list = ['t'] + stimulus.dynamic_parameters
        self.stored_data = []

    def update_list(self, data):
        self.check_start()
        self.stored_data.append(data)

