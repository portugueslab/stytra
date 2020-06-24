import numpy as np
import datetime


class Stimulus:
    """ Abstract class for a Stimulus.

    In stytra, a Stimulus is something that
    makes things happen at some point of an experiment.
    The Stimulus class is just a building block: successions of Stimuli
    are assembled in a meaningful order by
    :class:`Protocol.  <stytra.stimulation.Protocol>`
    objects.

    A Stimulus runs for a time defined by its duration. to do so, the
    ProtocolRunner compares at every time step the duration of the stimulus
    with the time elapsed from its beginning.
    Whenever the ProtocolRunner sets a new stimulus it calls its
    :meth:`Stimulus.start()  <Stimulus.start()>` method.
    By defining this method in subclasses, we can trigger events at
    the beginning of the stimulus (e.g., activate a Pyboard, send a TTL pulse
    or similar).
    At every successive time, until the end of the Stimulus, its
    :meth:`Stimulus.update()  <Stimulus.update()>` method is called. By
    defining this method in subclasses, we can trigger
    events throughout the length of the Stimulus time.


    Note
    ----
    Be aware that code in the :meth:`Stimulus.start()  <Stimulus.start()>`
    and :meth:`Stimulus.update()  <Stimulus.update()>`
    functions is executed within
    the Stimulus&main GUI process, therefore:

        1. Its temporal precision is limited to  **? # TODO do some check here**
        2. Slow functions would slow down the entire main process, especially if
           called at every time step.

    Stimuli have parameters that are important to be logged in the final
    metadata and parameters that are not relevant. The get_state() method
    used to generate the log saves all attributes not starting with _.


    Different stimuli categories are implemented subclassing this class, e.g.:

        - visual stimuli (children of PainterStimulus subclass);
        - ...


    Parameters
    ----------
    duration : float
         duration of the stimulus (s)
    Returns
    -------

    """

    def __init__(self, duration=0.0):
        """ """

        self.duration = duration

        self._started = None
        self._elapsed = 0.0  # time from the beginning of the stimulus
        self.name = "undefined"
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
        dict :
            dictionary with all the current parameters of the stimulus

        """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != "_":
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
        """Function called by the ProtocolRunner when a new stimulus is set.
        """
        self.real_time_start = datetime.datetime.now()

    def stop(self):
        """Function called by the ProtocolRunner when a new stimulus is set.
        """
        pass

    def initialise_external(self, experiment):
        """ Make a reference to the Experiment class inside the Stimulus.
        This is required to access from inside the Stimulus class to the
        Calibrator, the Pyboard, the asset directories with movies or the motor
        estimators for virtual reality.
        Also, the necessary preprocessing operations are handled here,
        such as loading images or videos.

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

    @property
    def dynamic_parameter_names(self):
        return [self.name + "_" + param for param in self.dynamic_parameters]

    def get_dynamic_state(self):
        """ """
        state_dict = {
            self.name + "_" + param: getattr(self, param, 0)
            for param in self.dynamic_parameters
        }
        return state_dict


class InterpolatedStimulus(DynamicStimulus):
    """Stimulus that interpolates its internal parameters with a data frame

    Parameters
    ----------
    df_param : DataFrame
        A Pandas DataFrame containing the values to be interpolated
        it has to contain a column named t for the defined time points,
        and additional columns for each parameter of the stimulus that is
        to be changed.
        A constant velocity of the parameter change can be specified,
        in that case the column name has to be prefixed with "vel_"

        Example:
        t | x
        -------
        0 | 1.0
        4 | 7.8

    """

    def __init__(self, *args, df_param, **kwargs):
        """"""
        super().__init__(*args, **kwargs)
        self.dynamic_parameters.append("current_phase")
        self.df_param = df_param
        self.duration = float(df_param.t.iat[-1])
        self.phase_times = np.unique(df_param.t)
        self.current_phase = 0
        self._past_t = 0
        self._dt = 1 / 60.0

    def update(self):
        """ """
        # to use parameters defined as velocities, we need the time
        # difference before previous display
        self._dt = self._elapsed - self._past_t
        self._past_t = self._elapsed

        # the phase has to be found by searching, as there are situation where it does not always increase
        self.current_phase = np.searchsorted(self.phase_times - 1e-9,
                                             self._elapsed) - 1

        for col in self.df_param.columns:
            if col != "t":
                # for defined velocities, integrates the parameter
                if col.startswith("vel_"):
                    setattr(
                        self,
                        col[4:],
                        getattr(self, col[4:])
                        + self._dt
                        * np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
                    )
                # otherwise it is set by interpolating the column of the
                # dataframe
                # else:
                setattr(
                    self,
                    col,
                    np.interp(self._elapsed, self.df_param.t, self.df_param[col]),
                )


class TriggerStimulus(DynamicStimulus):
    """ A class that uses the Experiment trigger to trigger a sequence
    of stimuli.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "trigger"
        self.duration = 0

    def start(self):
        # At the beginning we set this to infinity:
        self.duration = np.inf

    def update(self):
        # If trigger is set, make it end:
        if self._experiment.trigger.start_event.is_set():
            self.duration = self._elapsed


class CombinerStimulus(DynamicStimulus):
    """
    Class to have two stimuli happening pseudo-simultaneously (one update would
    still be called before the other one).
    """

    def __init__(self, stim_list):
        super().__init__()
        self._stim_list = stim_list

        self.duration = max([s.duration for s in stim_list])

        self.dynamic_parameters = self.dynamic_parameter_names

    def start(self):
        for s in self._stim_list:
            s.start()

        super().start()

    def stop(self):
        for s in self._stim_list:
            s.stop()

    def paint(self, p, w, h):
        for s in self._stim_list:
            s.paint(p, w, h)
            # p.end()

    def update(self):
        for s in self._stim_list:
            s.update()
            s._elapsed = self._elapsed

    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        for s in self._stim_list:
            s.initialise_external(experiment)

    @property
    def dynamic_parameter_names(self):
        names = []
        for i, s in enumerate(self._stim_list):
            if isinstance(s, DynamicStimulus):
                for n in s.dynamic_parameter_names:
                    names.append("s{}_{}".format(i, n))

        return names

    def get_dynamic_state(self):
        state = dict()
        for i, s in enumerate(self._stim_list):
            if isinstance(s, DynamicStimulus):
                d = s.get_dynamic_state()
                state.update({"s{}_{}".format(i, k): d[k] for k in d.keys()})

        return state

    def get_state(self):
        """
        """
        state_dict = dict()
        for key, value in self.__dict__.items():
            if not callable(value) and key[0] != "_":
                state_dict[key] = value

        for i, s in enumerate(self._stim_list):
            for key, value in s.__dict__.items():
                if not callable(value) and key[0] != "_":
                    state_dict["s{}_{}".format(i, key)] = value

        return state_dict
