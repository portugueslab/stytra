from PyQt5.QtCore import QObject
import datetime
import numpy as np
from queue import Empty
import pandas as pd
import json


class Accumulator:
    """Abstract class for accumulating streams of data.

    It is use to save or plot in real time data from stimulus logs or
    behaviour tracking. Data is stored in a list in the stored_data
    attribute.

    Specific methods
    for updating the stored_data list (e.g., by acquiring data from a
    Queue or a DynamicStimulus attribute) are defined in subclasses of the
    Accumulator.

    Data that end up in the stored_data list must be tuples where the first
    element is a timestamp.
    Therefore, stored_data of an Accumulator that is fed 2 values will be
    something like
    [(t_0, x_0, y_0), (t_0, x_0, y_0), ...]

    Headers from the n data points must be assigned to the header_list list.

    Data can be retrieved from the Accumulator as a pandas DataFrame with the
    :meth:`get_dataframe() <Accumulator.get_dataframe()>` method.


    Parameters
    ----------
    fps_calc_points : int
        number of data points used to calculate the sampling rate of the data.

    Returns
    -------

    """

    def __init__(self, fps_calc_points=10, monitored_headers=None):
        """ """
        self.stored_data = []
        self.header_list = ["t"]
        self.monitored_headers = (
            monitored_headers
        )  # headers which are included in the stream plot
        self.starting_time = None
        self.fps_calc_points = fps_calc_points

    def reset(self, header_list=None):
        """Reset accumulator and assign a new headers list.

        Parameters
        ----------
        header_list : list of str
             List with the headers Default value = None)

        Returns
        -------

        """
        if header_list is not None:
            self.header_list = ["t"] + header_list
        self.stored_data = []
        self.starting_time = None

    def check_start(self):
        """ """
        if self.starting_time is None:
            self.starting_time = datetime.datetime.now()

    def get_dataframe(self):
        """Returns pandas DataFrame with data and headers.
        """
        return pd.DataFrame(self.get_last_n(), columns=self.header_list)

    def get_fps(self):
        """ """
        try:
            last_t = self.stored_data[-1][0]
            t_minus_dif = self.stored_data[-self.fps_calc_points][0]
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

        if len(self.stored_data) == 0:
            return np.zeros(len(self.header_list)).reshape(1, len(self.header_list))
        else:
            data_list = self.stored_data[-max(last_n, 1):]

            # The length of the tuple in the accumulator may change. Here we
            # make sure we take only the elements that have the same
            # dimension as the last one.
            n_take = 1
            if len(data_list) > 2:
                for d in data_list[-2:0:-1]:
                    if len(d) == len(data_list[-1]):
                        n_take += 1
                    else:
                        break
            obar = np.array(data_list[-n_take:])
            return obar

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
        except OverflowError:
            return self.get_last_n(1)

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
        outpath = path + "." + format
        if format == "csv":
            self.get_dataframe().to_csv(outpath, sep=";")
        elif format == "feather":
            self.get_dataframe().to_feather(outpath)
        elif format == "hdf5":
            self.get_dataframe().to_hdf(outpath, "/data")
        elif format == "json":
            json.dump(self.get_dataframe().to_dict(), open(outpath, "w"))
        else:
            raise (NotImplementedError(format + " is not an implemented log foramt"))


class QueueDataAccumulator(QObject, Accumulator):
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

    def __init__(self, data_queue, header_list=None, **kwargs):
        """ """
        super().__init__(**kwargs)

        # Store externally the starting time make us free to keep
        # only time differences in milliseconds in the list (faster)
        self.starting_time = None

        self.data_queue = data_queue
        self.stored_data = []

        # First data column will always be time:
        self.header_list.extend(header_list)

    def update_list(self):
        """Upon calling put all available data into a list.
        """
        while True:
            try:
                # Get data from queue:
                t, data = self.data_queue.get(timeout=0.00001)

                # If we are at the starting time:
                if len(self.stored_data) == 0:
                    self.starting_time = t

                # Time in ms (for having np and not datetime objects)
                t_ms = (t - self.starting_time).total_seconds()

                # append:
                l = (t_ms,) + tuple(data)
                self.stored_data.append(l)
            except Empty:
                break


class DynamicLog(Accumulator):
    """Accumulator to save feature of a stimulus, e.g. velocity of gratings
    in a closed-loop experiment.

    Parameters
    ----------
    stimuli : list
        list of the stimuli to be logged

    """

    def __init__(self, stimuli):
        """ """

        super().__init__()
        # it is assumed the first dynamic stimulus has all the fields
        for stimulus in stimuli:
            try:
                self.header_list = ["t"] + stimulus.dynamic_parameters
            except AttributeError:
                pass
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


class EstimatorLog(Accumulator):
    """ """

    def __init__(self, headers):
        super().__init__()
        self.header_list = ("t",) + tuple(headers)
        self.stored_data = []

    def update_list(self, data):
        """

        Parameters
        ----------
        data :


        Returns
        -------

        """
        # delta_t = (datetime.datetime.now()-self.starting_time).total_seconds()
        self.check_start()
        self.stored_data.append(data)