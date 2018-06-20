import datetime
from copy import deepcopy

import numpy as np
from PyQt5.QtCore import pyqtSignal, QTimer, QObject
from stytra.collectors import Accumulator
from stytra.utilities import HasPyQtGraphParams


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

    Parameters
    ----------

    Returns
    -------

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
        """Set new Protocol.

        Parameters
        ----------
        protocol :
            Protocol object

        Returns
        -------

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
        """Set a new protocol from its name. Uses the dictionary of protocols
        generated from the stytra.stimulation.protocols file.

        Parameters
        ----------
        protocol_name :
            string with the protocol name.

        Returns
        -------

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
        """Update current Protocol (get a new stimulus list if protocol or"""
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
        """Make the protocol ready to start again. Reset all ProtocolRunner
        and stimuli timers and elapsed times.

        Parameters
        ----------

        Returns
        -------

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
        if self.experiment.trigger is None:
            self._start()
        else:
            while True:
                if self.experiment.trigger.start_event.is_set() and \
                   not self.running:
                    self._start()
                    break
                else:
                    self.experiment.app.processEvents()

    def _start(self):
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
        """Update displayed stimulus. This function is the core of the
        ProtocolRunner class. It is called by every timer timeout.
        At every timesteps, if protocol is running:
        
         - check elapsed time from beginning of the last stimulus;
         - if required, update current stimulus state
         - if elapsed time has passed stimulus duration, change current
           stimulus.

        Parameters
        ----------

        Returns
        -------

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

            self.current_stimulus.update()  # use stimulus update function
            self.sig_timestep.emit(self.i_current_stimulus)

            # If stimulus is a constantly changing stimulus:
            if isinstance(self.current_stimulus, DynamicStimulus):
                self.sig_stim_change.emit(self.i_current_stimulus)
                self.update_dynamic_log()  # update dynamic log for stimulus

    def stop(self):
        """Stop the stimulation sequence. Update log and stop timer."""
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
        """Append the log appending info from the last stimulus. Add to the
        stimulus info from Stimulus.get_state() start and stop times.

        Parameters
        ----------

        Returns
        -------

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
        """Update a dynamic log. Called only if one is present."""
        self.dynamic_log.update_list((self.t, ) +
                self.current_stimulus.get_dynamic_state())

    def get_duration(self):
        """Get total duration of the protocol in sec, calculated from stimuli
        durations.
        :return: protocol length in seconds

        Parameters
        ----------

        Returns
        -------

        """
        total_duration = 0
        for stim in self.stimuli:
            total_duration += stim.duration
        return total_duration

    def print(self):
        """Print protocol sequence."""
        string = ''
        for stim in self.stimuli:
            string += '-' + stim.name

        print(string)


# TODO maybe this should be defined elsewhere
class DynamicLog(Accumulator):
    """ """
    def __init__(self, stimuli):
        super().__init__()
        # it is assumed the first dynamic stimulus has all the fields
        for stimulus in stimuli:
            if isinstance(stimulus, DynamicStimulus):
                self.header_list = ['t'] + stimulus.dynamic_parameters
        self.stored_data = []

    def update_list(self, data):
        """

        Parameters
        ----------
        data :
            

        Returns
        -------

        """
        self.check_start()
        self.stored_data.append(data)


class Protocol(HasPyQtGraphParams):
    """The Protocol class is thought as an easily subclassable class that
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

    Parameters
    ----------

    Returns
    -------

    """

    name = ''

    def __init__(self):
        """
        Add standard parameters common to all kind of protocols.
        """
        super().__init__(name='stimulus_protocol_params')

        for child in self.params.children():
            self.params.removeChild(child)

        self.add_params(name=self.name,
                        n_repeats=1,
                        pre_pause=0.,
                        post_pause=0.)


    def get_stimulus_list(self):
        """Generate protocol from specified parameters. Called by the
        ProtocolRunner class where the Protocol instance is defined.
        This function puts together the stimulus sequence defined by each
        child class with the initial and final pause and repeats it the
        specified number of times. It should not change in subclasses.

        Parameters
        ----------

        Returns
        -------

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
        """To be specified in each child class to return the proper list of
        stimuli.

        Parameters
        ----------

        Returns
        -------

        """
        return []


class Stimulus:
    """General class for a Stimulus. In stytra, a Stimulus is something that
    makes things happen at some point of an experiment.
    The Stimulus class is just a building block: successions of Stimuli
    are assembled in a meaningful order by Protocol objects.
    
    A Stimulus runs for a time defined by its duration. to do so, the
    ProtocolRunner compares at every time step the duration of the stimulus
    with the time elapsed from its beginning.
    
    Whenever the ProtocolRunner sets a new stimulus it calls its start() method.
    By defining this method in subclasses, we can trigger events at
    the beginning of the stimulus (e.g., activate a Pyboard, send a TTL pulse
     or similar).
    
    At every successive time, until the end of the Stimulus, its update()
    method is called. By defining this method in subclasses, we can trigger
    events throughout the length of the Stimulus time.
    
    Be aware that code in the start() and update() functions is executed within
    the Stimulus&main GUI process, therefore:
     1. Its temporal precision is limited to # TODO do some check here
     2. Slow functions would slow down the entire main process, especially if
        called at every time step.
    
    Stimului have parameters that are important to be logged in the final
    metadata and parameters that are not relevant. The get_state() method
    used to generate the log saves all attributes not starting with _.
    
    
    Different stimuli categories are implemented subclassing this class, e.g.:
     - visual stimuli (children of PainterStimulus subclass);
     ...

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, duration=0.0):
        """
        Make a stimulus, with the basic properties common to all stimuli.
        Values not to be logged start with _

        :param duration: duration of the stimulus (s)
        """

        self.duration = duration

        self._started = None
        self._elapsed = 0.0  # time from the beginning of the stimulus
        self.name = ''
        self._experiment = None
        self.real_time_start = None
        self.real_time_stop = None

    def get_state(self):
        """Returns a dictionary with stimulus features for logging.
        Ignores the properties which are private (start with _)

        Parameters
        ----------

        Returns
        -------

        """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != '_':
                state_dict[key] = value
        return state_dict

    def update(self):
        """Function called by the ProtocolRunner every timestep until the Stimulus
        is over.

        Parameters
        ----------

        Returns
        -------

        """
        self.real_time_stop = datetime.datetime.now()

    def start(self):
        """Function called by the ProtocolRunner when a new stimulus is set."""
        self.real_time_start = datetime.datetime.now()

    def initialise_external(self, experiment):
        """Make a reference to the Experiment class inside the Stimulus.
        This is required to access from inside the Stimulus class to the
        Calibrator, the Pyboard, the asset directories with movies or the motor
        estimator for virtual reality.

        Parameters
        ----------
        experiment :
            the experiment object to which link the stimulus

        Returns
        -------
        type
            None

        """
        self._experiment = experiment


class DynamicStimulus(Stimulus):
    """Stimuli where parameters change during stimulation on a frame-by-frame
    base.
    It implements the recording changing parameters.

    Parameters
    ----------

    Returns
    -------

    """
    def __init__(self, *args, dynamic_parameters=None, **kwargs):
        """
        :param dynamic_parameters: A list of all parameters that are to be
                                   recorded frame by frame;
        """
        super().__init__(*args, **kwargs)
        if dynamic_parameters is None:
            self.dynamic_parameters = []
        else:
            self.dynamic_parameters = dynamic_parameters

    def get_dynamic_state(self):
        """ """
        return tuple(getattr(self, param, 0)
                     for param in self.dynamic_parameters)


class InterpolatedStimulus(Stimulus):
    """Stimulus that interpolates its internal parameters with a data frame"""
    def __init__(self, *args, df_param, **kwargs):
        """"""
        super().__init__(*args, **kwargs)
        self.df_param = df_param
        self.duration = float(df_param.t.iat[-1])

    def update(self):
        """ """
        for col in self.df_param.columns:
            if col != "t":
                try:
                    setattr(self, col, np.interp(self._elapsed, self.df_param.t,
                                                 self.df_param[col]))

                except (AttributeError, KeyError):
                    pass