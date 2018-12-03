import datetime
from copy import deepcopy

from PyQt5.QtCore import pyqtSignal, QTimer, QObject
from stytra.stimulation.stimuli import Pause, DynamicStimulus
from stytra.collectors.accumulators import DynamicLog
from lightparam.param_qt import ParametrizedQt, Param

import logging


class ProtocolRunner(QObject):
    """Class for managing and running stimulation Protocols.

    It is thought to be
    integrated with the stytra.gui.protocol_control.ProtocolControlWidget GUI.
    
    In stytra Protocols are parameterized objects required just for generating
    a list of Stimulus objects. The engine that run this sequence of Stimuli
    is the ProtocolRunner class.
    A ProtocolRunner instance is not bound to a single Protocol object:

        - new Protocols can be set via the self.set_new_protocol() function;
        - current Protocol can be updated (e.g., after changing parameters).


    New Protocols are set by their name (a way for restoring state
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


    Parameters
    ----------
    experiment : :obj:`stytra.experiment.Experiment`
        the Experiment object where directory, calibrator *et similia*
        will be found.
    dt : float
         (optional) timestep for protocol updating.
    log_print : Bool
        (optional) if True, print stimulus log.
    protocol : str
        (optional) name of protocol to be set at the beginning.


    **Signals**
    """

    sig_timestep = pyqtSignal(int)
    """Emitted at every timestep with the index of the current stimulus."""
    sig_stim_change = pyqtSignal(int)
    """Emitted every change of stimulation, with the index of the new
    stimulus."""
    sig_protocol_started = pyqtSignal()
    """Emitted when the protocol sequence starts."""
    sig_protocol_finished = pyqtSignal()
    """Emitted when the protocol sequence ends."""
    sig_protocol_updated = pyqtSignal()  # parameters changed in the protocol
    """Emitted when protocol is changed/updated"""

    def __init__(self, experiment=None, log_print=True, protocol=None):
        """ """
        super().__init__()

        self.experiment = experiment

        self.t_start = None
        self.t_end = None
        self.completed = False
        self.t = 0

        self.timer = QTimer()

        self.protocol = experiment.protocol
        self.stimuli = []
        self.i_current_stimulus = None  # index of current stimulus
        self.current_stimulus = None  # current stimulus object
        self.past_stimuli_elapsed = None  # time elapsed in previous stimuli
        self.duration = None  # total duration of the protocol
        self.dynamic_log = None  # dynamic log for stimuli

        # self.prot_class_dict = {c.name: c for c in experiment.protocols}
        self._set_new_protocol(self.protocol)
        self.update_protocol()
        self.protocol.sig_param_changed.connect(self.update_protocol)

        # Log will be a list of stimuli states:
        self.log = []
        self.log_print = log_print
        self.running = False

    def _set_new_protocol(self, protocol):
        """Set new Protocol.

        Parameters
        ----------
        protocol : :obj:`stytra.experiment.Protocol`
            Protocol to be set.

        """
        if protocol is not None:
            self.protocol = protocol

            self.update_protocol()
            # Connect changes to protocol parameters to update function:
            self.protocol.sig_param_changed.connect(self.update_protocol)
            self.experiment.dc.add(self.protocol)

            # Why were we resetting here?
            self.reset()
            self.sig_protocol_updated.emit()

    def update_protocol(self):
        """Update current Protocol (get a new stimulus list if protocol
        exist.
        """
        if self.protocol is not None:
            self.stimuli = self.protocol._get_stimulus_list()

            self.current_stimulus = self.stimuli[0]

            # pass experiment to stimuli for calibrator and asset folders:
            for stimulus in self.stimuli:
                stimulus.initialise_external(self.experiment)

            if self.dynamic_log is None:
                self.dynamic_log = DynamicLog(self.stimuli)
            else:
                self.dynamic_log.update_stimuli(self.stimuli)  # new stimulus log

            self.duration = self.get_duration()  # set new duration

            self.sig_protocol_updated.emit()

    def reset(self):
        """Make the protocol ready to start again. Reset all ProtocolRunner
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
        """Start the protocol by starting the timers.
        """
        # Updating protocol before starting has been added to include changes
        #  to the calibrator that are considered only in initializing the
        # stimulus and not while it is running (e.g., gratings). Consider
        # removing if it slows down significantly the starting event.
        self.update_protocol()

        self.experiment.logger.info("{} protocol started...".format(self.protocol.name))
        self.t_start = datetime.datetime.now()  # get starting time
        self.timer.timeout.connect(self.timestep)  # connect timer to update fun
        self.timer.setSingleShot(False)
        self.timer.start()  # start the timer
        self.dynamic_log.reset()  # reset the log
        self.log = []
        self.past_stimuli_elapsed = datetime.datetime.now()
        self.current_stimulus.started = datetime.datetime.now()
        self.sig_protocol_started.emit()
        self.running = True
        self.current_stimulus.start()

    def timestep(self):
        """Update displayed stimulus. This function is the core of the
        ProtocolRunner class. It is called by every timer timeout.
        At every timestep, if protocol is running:
        
            - check elapsed time from beginning of the last stimulus;
            - if required, update current stimulus state
            - if elapsed time has passed stimulus duration, change current
            stimulus.


        """
        if self.running:
            # Get total time from start in seconds:
            self.t = (datetime.datetime.now() - self.t_start).total_seconds()

            # Calculate elapsed time for current stimulus:
            self.current_stimulus._elapsed = (
                datetime.datetime.now() - self.past_stimuli_elapsed
            ).total_seconds()

            # If stimulus time is over:
            if self.current_stimulus._elapsed > self.current_stimulus.duration:
                self.current_stimulus.stop()
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
                        seconds=float(self.current_stimulus.duration)
                    )
                    self.i_current_stimulus += 1
                    self.current_stimulus = self.stimuli[self.i_current_stimulus]
                    self.current_stimulus.start()

            self.current_stimulus.update()  # use stimulus update function
            self.sig_timestep.emit(self.i_current_stimulus)

            # If stimulus is a constantly changing stimulus:
            if isinstance(self.current_stimulus, DynamicStimulus):
                self.sig_stim_change.emit(self.i_current_stimulus)
                self.update_dynamic_log()  # update dynamic log for stimulus

    def stop(self):
        """Stop the stimulation sequence. Update log and stop timer.
        """
        if not self.completed:  # if protocol was interrupted, update log anyway
            self.update_log()
            self.experiment.logger.info(
                "{} protocol interrupted.".format(self.protocol.name)
            )
        else:
            self.experiment.logger.info(
                "{} protocol finished.".format(self.protocol.name)
            )

        if self.running:
            self.running = False
            self.t_end = datetime.datetime.now()
            # try:
            self.timer.timeout.disconnect()
            self.timer.stop()
            # except:
            #     pass

    def update_log(self):
        """Append the log appending info from the last stimulus. Add to the
        stimulus info from Stimulus.get_state() start and stop times.

        """
        # Update with the data of the current stimulus:
        current_stim_dict = self.current_stimulus.get_state()
        t_stim_stop = current_stim_dict["real_time_stop"] or datetime.datetime.now()
        try:
            new_dict = dict(
                current_stim_dict,
                t_start=(
                    current_stim_dict["real_time_start"] - self.t_start
                ).total_seconds(),
                t_stop=(t_stim_stop - self.t_start).total_seconds(),
            )
        except TypeError as e:  # if time is None stimulus was not run
            new_dict = dict()
            logging.getLogger().info("Stimulus times incorrect, state not saved")
        self.log.append(new_dict)

    def update_dynamic_log(self):
        """
        Update a dynamic log. Called only if one is present.
        """

        self.dynamic_log.update_list(self.t, self.current_stimulus.get_dynamic_state())

    def get_duration(self):
        """Get total duration of the protocol in sec, calculated from stimuli
        durations.

        Returns
        -------
        float :
            protocol length in seconds.

        """
        total_duration = 0
        for stim in self.stimuli:
            total_duration += stim.duration
        return total_duration

    def print(self):
        """Print protocol sequence.
        """
        string = ""
        for stim in self.stimuli:
            string += "-" + stim.name

        print(string)


class Protocol(ParametrizedQt):
    """Describe a sequence of Stimuli and their parameters.

    The Protocol class is thought as an easily subclassable class that
    generate a list of stimuli according to some parameterization.
    It basically constitutes a way of keeping together:

        - the parameters that describe the protocol;
        - the function to generate the list of stimuli.


    The method :meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>`
    is the core of the class: it is called
    by the ProtocolRunner and it generates a list with the stimuli that
    have to be presented in the protocol.
    When defining new protocols we will subclass this class and redefine
    :meth:`Protocol.get_stim_sequence()
    <stytra.stimulation.protocols.Protocol.get_stim_sequence()>`.

    By default, all protocols have an initial and final pause and a parameter
    n_repetitions that specifies the number of times the sequence from
    :meth:`Protocol.get_stim_sequence() <stytra.stimulation.protocols.Protocol.get_stim_sequence()>`
    has to be repeated.



    Note
    ----
    Everything concerning
    calibration, or asset directories that have to be passed to the
    stimulus is handled in the ProtocolRunner class to leave this class
    as light as possible.


    Parameters
    ----------

    Returns
    -------

    """

    name = ""
    """Name of the protocol."""

    def __init__(self):
        """
        Add standard parameters common to all kind of protocols.
        """
        try:
            assert len(self.__class__.name) > 0
        except AssertionError:
            raise ValueError("Protocol does not have a specified name")
        super().__init__(name="stimulus/protocol/" + self.__class__.name)

        self.pre_pause = Param(0.)
        self.post_pause = Param(0.)
        self.n_repeats = Param(1, limits=(1, 10000))

    def _get_stimulus_list(self):
        """Generate protocol from specified parameters. Called by the
        ProtocolRunner class where the Protocol instance is defined.
        This function puts together the stimulus sequence defined by each
        child class with the initial and final pause and repeats it the
        specified number of times. It should not change in subclasses.

        Parameters
        ----------

        Returns
        -------
        list :
            list of stimuli

        """
        main_stimuli = self.get_stim_sequence()
        stimuli = []
        if self.pre_pause > 0:
            stimuli.append(Pause(duration=self.pre_pause))  # self.params[
            # "pre_pause"]))

        for i in range(self.n_repeats):
            stimuli.extend(deepcopy(main_stimuli))

        if self.post_pause > 0:
            stimuli.append(Pause(duration=self.post_pause))

        return stimuli

    def get_stim_sequence(self):
        """To be specified in each child class to return the proper list of
        stimuli.

        Parameters
        ----------

        Returns
        -------

        """
        return []
