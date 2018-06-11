import datetime

from PyQt5.QtCore import pyqtSignal, QTimer, QObject

from stytra.stimulation.stimuli import DynamicStimulus, Pause
from stytra.collectors import Accumulator

from stytra.stimulation import protocols
from stytra.stimulation.protocols import Protocol

import inspect
from collections import OrderedDict


def get_classes_from_module(input_module, parent_class):
    """ Find all the classes in a module that are children of a parent one.

    :param input_module: module object
    :param parent_class: parent class object
    :return: OrderedDict of subclasses found
    """
    classes = inspect.getmembers(input_module, inspect.isclass)
    ls_classes = OrderedDict({c[1].name: c[1] for c in classes
                              if issubclass(c[1], parent_class)
                              and not c[1] is parent_class})

    return ls_classes


class ProtocolRunner(QObject):
    """
    Class for managing and running stimulation Protocols. It is thought to be
    integrated with the stytra.gui.protocol_control.ProtocolControlWidget GUI.

    In stytra Protocols are parameterized objects required just for generating
    a list of Stimulus objects. The engine that run this sequence of Stimuli
    is the ProtocolRunner class.

    A ProtocolRunner instance is not bound to a single Protocol object:
     - new Protocols can be set via the self.set_new_protocol() function;
     - current Protocol can be updated (e.g., after changing parameters).

    The list of the available protocols is generated automatically by looking
    at the Protocol subclasses defined in the stytra.stimulation.protocols
    module. New Protocols are set by their name (a way for restoring state
    from the config.h5 file), but can also be set by passing a Protocol() class
    to the internal _set_new_protocol() method.

    Every time a Protocol is set or updated, the ProtocolRunner uses its
    get_stimulus_sequence() method to generate a new list of stimuli.

    For running the Protocol (i.e., going through the list of Stimulus objects
    keeping track of time), ProtocolRunner has an internal QTimer whose timeout
    calls the timestep() method, which:
     - checks elapsed time from beginning of the last stimulus;
     - if required, updates current stimulus state
     - if elapsed time has passed stimulus duration, changes current
       stimulus.

    ====================== ====================================================
    **Signals**
    sig_timestep           Emitted at every timestep, with the index of the
                           current stimulus.
    sig_stim_change        Emitted every change of stimulation, with the index
                           of the new stimulus.
    sig_protocol_started   Emitted when the protocol sequence starts.
    sig_protocol_finished  Emitted when the protocol sequence ends.
    sig_protocol_updated   Emitted when protocol is changed/updated
    ====================== ====================================================
    """

    sig_timestep = pyqtSignal(int)
    sig_stim_change = pyqtSignal(int)
    sig_protocol_started = pyqtSignal()
    sig_protocol_finished = pyqtSignal()
    sig_protocol_updated = pyqtSignal()  # parameters changed in the protocol

    def __init__(self, experiment=None, dt=1/60,
                 log_print=True, protocol=None):
        """
        :param dt: timestep for protocol updating;
        :param log_print: if True, print stimulus log;
        :param experiment: the Experiment class where directory,
                           calibrator et similia will be found;
        :param protocol:  protocol set instantiating the ProtocolRunner.
        """
        super().__init__()

        self.experiment = experiment

        self.t_start = None
        self.t_end = None
        self.completed = False
        self.t = 0

        # TODO do we need this dt?
        self.dt = dt
        self.timer = QTimer()

        self.protocol = None
        self.stimuli = []
        self.i_current_stimulus = None  # index of current stimulus
        self.current_stimulus = None  # current stimulus object
        self.past_stimuli_elapsed = None  # time elapsed in previous stimuli
        self.duration = None  # total duration of the protocol
        self.dynamic_log = None  # dynamic log for stimuli

        self.prot_class_dict = {c.name: c for c in experiment.protocols}
        self.set_new_protocol(protocol)
        self.sig_protocol_updated.emit()

        # Log will be a list of stimuli states:
        self.log = []
        self.log_print = log_print
        self.running = False

    def _set_new_protocol(self, protocol):
        """
        Set new Protocol.
        :param protocol: Protocol object
        """
        # If there was a protocol before, block params signal to avoid duplicate
        # calls of the ProtocolRunner update_protocol function.
        # Otherwise it would be called by the change of the params three caused
        # by its deletion from the  _params called in the Protocol __init__().
        if protocol is not None:
            if self.protocol is not None:
                self.protocol.params.blockSignals(True)

            self.protocol = protocol

            self.update_protocol()

            # Connect changes to protocol parameters to update function:
            self.protocol.params.sigTreeStateChanged.connect(
                self.update_protocol)

            # Why were we resetting here?
            self.reset()

    def set_new_protocol(self, protocol_name):
        """
        Set a new protocol from its name. Uses the dictionary of protocols
        generated from the stytra.stimulation.protocols file.
        :param protocol_name: string with the protocol name.
        """
        if protocol_name is not None:
            try:
                ProtocolClass = self.prot_class_dict[protocol_name]
                protocol = ProtocolClass()
                self._set_new_protocol(protocol)

                self.sig_protocol_updated.emit()
            except KeyError:
                print('protocol in the config file is not defined in the '
                      'protocols file')

    def update_protocol(self):
        """
        Update current Protocol (get a new stimulus list if protocol or
        parameters are changed).
        """
        if self.protocol is not None:
            self.stimuli = self.protocol.get_stimulus_list()

            self.current_stimulus = self.stimuli[0]

            # pass experiment to stimuli for calibrator and asset folders:
            for stimulus in self.stimuli:
                stimulus.initialise_external(self.experiment)

            self.dynamic_log = DynamicLog(self.stimuli)  # new stimulus log
            self.duration = self.get_duration()  # set new duration

            self.sig_protocol_updated.emit()

    def reset(self):
        """
        Make the protocol ready to start again. Reset all ProtocolRunner
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
        """
        Start the protocol by starting the timers.
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
        self.current_stimulus.start()

    def timestep(self):
        """
        Update displayed stimulus. This function is the core of the
        ProtocolRunner class. It is called by every timer timeout.
        At every timesteps, if protocol is running:

         - check elapsed time from beginning of the last stimulus;
         - if required, update current stimulus state
         - if elapsed time has passed stimulus duration, change current
           stimulus.
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
                    print('pre')
                    print(self.current_stimulus.real_time_start)
                    self.current_stimulus.start()
                    print('post')
                    print(self.current_stimulus.real_time_start)

            self.current_stimulus.update()  # use stimulus update function
            self.sig_timestep.emit(self.i_current_stimulus)

            # If stimulus is a constantly changing stimulus:
            if isinstance(self.current_stimulus, DynamicStimulus):
                self.sig_stim_change.emit(self.i_current_stimulus)
                self.update_dynamic_log()  # update dynamic log for stimulus

    def stop(self):
        """
        Stop the stimulation sequence. Update log and stop timer.
        """
        if not self.completed:  # if protocol was interrupted, update log anyway
            self.update_log()

        if self.running:
            self.running = False
            self.t_end = datetime.datetime.now()
            try:
                self.timer.timeout.disconnect()
                self.timer.stop()
            except:  # TODO generic except
                pass

    def update_log(self):
        """
        Append the log appending info from the last stimulus. Add to the
        stimulus info from Stimulus.get_state() start and stop times.
        """
        # Update with the data of the current stimulus:
        current_stim_dict = self.current_stimulus.get_state()
        try:
            new_dict = dict(current_stim_dict,
                            t_start=(current_stim_dict['real_time_start'] -
                                     self.t_start).total_seconds(),
                            t_stop=(current_stim_dict['real_time_stop'] -
                                    self.t_start).total_seconds())
        except TypeError:  # if time is None stimulus was not run
            new_dict = dict()

        self.log.append(new_dict)

    def update_dynamic_log(self):
        """
        Update a dynamic log. Called only if one is present.
        """
        self.dynamic_log.update_list((self.t, ) +
                self.current_stimulus.get_dynamic_state())

    def get_duration(self):
        """
        Get total duration of the protocol in sec, calculated from stimuli
        durations.
        :return: protocol length in seconds
        """
        total_duration = 0
        for stim in self.stimuli:
            total_duration += stim.duration
        return total_duration

    def print(self):
        """
        Print protocol sequence.
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

