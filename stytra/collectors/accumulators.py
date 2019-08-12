from PyQt5.QtCore import QObject, pyqtSignal
import datetime
import numpy as np
from queue import Empty
import pandas as pd
from collections import namedtuple
from bisect import bisect_right
from os.path import basename

from stytra.utilities import save_df


class Accumulator(QObject):
    def __init__(self, experiment, name="", max_history_if_not_running=1000):
        super().__init__()
        self.name = name
        self.exp = experiment
        self.stored_data = []
        self.times = []
        self.max_history_if_not_running = max_history_if_not_running


class DataFrameAccumulator(Accumulator):
    """Abstract class for accumulating streams of data.

    It is use to save or plot in real time data from stimulus logs or
    behavior tracking. Data is stored in a list in the stored_data
    attribute.

    Specific methods
    for updating the stored_data list (e.g., by acquiring data from a
    Queue or a DynamicStimulus attribute) are defined in subclasses of the
    Accumulator.

    Data that end up in the stored_data list must be NamedTuples where the first
    element is a timestamp.
    Therefore, stored_data of an Accumulator that is fed 2 values will be
    something like
    [(t_0, x_0, y_0), (t_0, x_0, y_0), ...]


    Data can be retrieved from the Accumulator as a pandas DataFrame with the
    :meth:`get_dataframe() <Accumulator.get_dataframe()>` method.


    Parameters
    ----------
    fps_calc_points : int
        number of data points used to calculate the sampling rate of the data.

    Returns
    -------

    """

    """Emitted every change of stimulation, with the index of the new
        stimulus."""
    sig_acc_reset = pyqtSignal()
    sig_acc_init = pyqtSignal()

    def __init__(self, *args, fps_calc_points=10, monitored_headers=None, **kwargs):
        super().__init__(*args, **kwargs)
        """ """
        self.plot_columns = monitored_headers
        self.fps_calc_points = fps_calc_points
        self._header_dict = None

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return np.array(getattr(k, item[1]) for k in self.stored_data[item[0]])

        if isinstance(item, str):
            return np.array(getattr(k, item[1]) for k in self.stored_data)

    @property
    def t(self):
        return np.array(self.times)

    def values_at_abs_time(self, time):
        """ Finds the values in the accumulator closest to the datetime time

        Parameters
        ----------
        time : datetime
            time to search for

        Returns
        -------
        namedtuple of values

        """
        find_time = (time - self.exp.t0).total_seconds()
        i = bisect_right(self.times, find_time)
        return self.stored_data[i - 1]

    @property
    def columns(self):
        try:
            return ("t",) + self.stored_data[-1]._fields
        except IndexError:
            raise ValueError("Accumulator empty, data types not known")

    @property
    def header_dict(self):
        """  for each header name gives the column
        """
        if self._header_dict is None:
            self._header_dict = {hn: i for i, hn in enumerate(self.columns)}
        return self._header_dict

    def reset(self, monitored_headers=None):
        """Reset accumulator and assign a new headers list.

        Parameters
        ----------
        monitored_headers : list of str
             List with the headers displayed by default Default value = None)

        Returns
        -------

        """
        self.sig_acc_reset.emit()
        if monitored_headers is not None:
            self.plot_columns = monitored_headers

        self.stored_data = []
        self.times = []

        self._header_dict = None

    def trim_data(self):
        if (
            not self.exp.protocol_runner.running
            and len(self.times) > self.max_history_if_not_running * 1.5
        ):
            self.times[: -self.max_history_if_not_running] = []
            self.stored_data[: -self.max_history_if_not_running] = []

    def get_fps(self):
        """ """
        try:
            last_t = self.times[-1]
            t_minus_dif = self.times[-self.fps_calc_points]
            return self.fps_calc_points / (last_t - t_minus_dif)
        except (IndexError, ValueError, ZeroDivisionError, OverflowError):
            return 0.0

    def get_last_n(self, n=None):
        """Return the last n data points.

        Parameters
        ----------
        n : int
            number of data points to be returned


        Returns
        -------
        np.array
            NxJ Array containing the last n data points, where J is the
            number of values collected at each timepoint + 1 (the timestamp)

        """
        if n is not None:
            last_n = min(n, len(self.stored_data))
        else:
            last_n = len(self.stored_data)

        if last_n == 0:
            return None

        df = pd.DataFrame.from_records(
            self.stored_data[-last_n:], columns=self.stored_data[-1]._fields
        )
        df["t"] = np.array(self.times[-last_n:])
        return df

    def get_last_t(self, t):
        """

        Parameters
        ----------
        t : float
            Time window in seconds from which data should be returned


        Returns
        -------
        np.array
            NxJ Array containing the last n data points, where J is the
            number of values collected at each timepoint + 1 (the timestamp)
            and N is t*fps


        """
        try:
            n = int(self.get_fps() * t)
            return self.get_last_n(n)
        except (OverflowError, ValueError):
            return self.get_last_n(1)

    def get_dataframe(self):
        """Returns pandas DataFrame with data and headers.
        """
        return self.get_last_n(len(self.stored_data))

    def save(self, path, format="csv"):
        """ Saves the content of the accumulator in a tabular format.
        Choose CSV for widest compatibility, HDF if using Python only,
        or feather for efficient storage compatible with Python and Julia
        data frames

        Parameters
        ----------
        path : str
            output path, without extension name
        format : str
            output format, csv, feather, hdf5, json

        """
        df = self.get_dataframe()
        if df is None:
            return
        saved_filename = save_df(df, path, format)
        return basename(saved_filename)

    def is_empty(self):
        return len(self.stored_data) == 0


class QueueDataAccumulator(DataFrameAccumulator):
    """General class for retrieving data from a Queue.

    The QueueDataAccumulator takes as input a multiprocessing.Queue object
    and retrieves data from it whenever its :meth:`update_list()
    <QueueDataAccumulator.update_list()>` method is called.
    All the data are then put in the stored_data list.
    It is usually connected with a QTimer() timeout to make sure that data
    from the Queue are constantly retrieved.

    Parameters
    ----------
    data_queue : (multiprocessing.Queue object)
        queue from witch to retrieve data.
    header_list : list of str
        headers for the data to stored.

    Returns
    -------

    """

    def __init__(self, data_queue, **kwargs):
        """ """
        super().__init__(**kwargs)

        # Store externally the starting time make us free to keep
        # only time differences in milliseconds in the list (faster)
        self.starting_time = None
        self.data_queue = data_queue

    def update_list(self):
        """Upon calling put all available data into a list.
        """
        while True:
            try:
                # Get data from queue:
                t, data = self.data_queue.get(timeout=0.001)
                newtype = False
                if len(self.stored_data) == 0 or type(data) != type(
                    self.stored_data[-1]
                ):
                    self.reset()
                    newtype = True

                # Time in ms (for having np and not datetime objects)
                t_s = (t - self.exp.t0).total_seconds()

                # append:
                self.times.append(t_s)
                self.stored_data.append(data)

                self.trim_data()

                # if the data type changed, emit a signal
                if newtype:
                    self.sig_acc_init.emit()
            except Empty:
                break


class FramerateAccumulator(Accumulator):
    def __init__(self, *args, goal_framerate=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.goal_framerate = goal_framerate

    def trim_data(self):
        if len(self.times) > self.max_history_if_not_running * 1.5:
            self.times[: -self.max_history_if_not_running] = []
            self.stored_data[: -self.max_history_if_not_running] = []

    def reset(self):
        self.times = []
        self.stored_data = []

    def update_list(self, fps):
        self.stored_data.append(fps)
        self.times.append((datetime.datetime.now() - self.exp.t0).total_seconds())


class FramerateQueueAccumulator(FramerateAccumulator):
    """A simple accumulator, just for framerates"""

    def __init__(self, *args, queue, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def update_list(self):
        while True:
            try:
                # Get data from queue:
                t, fps = self.queue.get(timeout=0.001)
                # Time in ms (for having np and not datetime objects)
                t_s = (t - self.exp.t0).total_seconds()

                # append:
                self.times.append(t_s)
                self.stored_data.append(fps)

                self.trim_data()

            except Empty:
                break


class DynamicLog(DataFrameAccumulator):
    """Accumulator to save feature of a stimulus, e.g. velocity of gratings
    in a closed-loop experiment.

    Parameters
    ----------
    stimuli : list
        list of the stimuli to be logged

    """

    def __init__(self, stimuli, **kwargs):
        """ """
        self.name = "stimulus_params"
        self._tupletype = None
        super().__init__(**kwargs)
        # it is assumed the first dynamic stimulus has all the fields

        self.update_stimuli(stimuli)

    @property
    def columns(self):
        try:
            return ("t",) + self._tupletype._fields
        except IndexError:
            raise ValueError("Data type not set for stimulus log")

    def update_list(self, time, data):
        """

        Parameters
        ----------
        data :


        Returns
        -------

        """
        self.times.append(time)
        self.stored_data.append(
            self._tupletype(*(data.get(f, np.nan) for f in self._tupletype._fields))
        )

    def update_stimuli(self, stimuli):
        dynamic_params = []
        for stimulus in stimuli:
            try:
                for new_param in stimulus.dynamic_parameter_names:
                    if not new_param in dynamic_params:
                        dynamic_params.append(new_param)
            except AttributeError:
                pass
        self._tupletype = namedtuple("s", dynamic_params)
        self.reset()


class EstimatorLog(DataFrameAccumulator):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stored_data = []

    def update_list(self, t, data):
        """

        Parameters
        ----------
        data :


        Returns
        -------

        """
        self.times.append(t)
        self.stored_data.append(data)

        self.trim_data()

        if len(self.stored_data) == 1:
            self.sig_acc_init.emit()
