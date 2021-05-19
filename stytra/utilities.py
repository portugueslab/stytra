import datetime
import json
import time
from collections import OrderedDict
from multiprocessing import Process, Queue
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from datetime import datetime

from numba import jit
from scipy.interpolate import interp1d

import numpy as np
import pandas as pd
import inspect

from pathlib import Path
import collections
from collections import namedtuple


class Database:
    """ """

    def __init__(self):
        pass

    def inset_experiment_data(self, exp_data):
        """

        Parameters
        ----------
        exp_data : the data collector dictionary
            

        Returns
        -------
        index of database entry

        """
        pass


class FramerateRecorder:
    def __init__(self, n_fps_frames=5):
        # Set framerate calculation parameters
        self.n_fps_frames = n_fps_frames
        self.i_fps = 0
        self.previous_time_fps = None
        self.current_framerate = None

        # Store current time timestamp:
        self.current_time = datetime.now()
        self.starting_time = datetime.now()

    def update_framerate(self):
        """Calculate the framerate every n_fps_frames frames."""
        # If number of frames for updating is reached:
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                try:
                    self.current_framerate = (
                        self.n_fps_frames
                        / (self.current_time - self.previous_time_fps).total_seconds()
                    )
                except ZeroDivisionError:
                    self.current_framerate = 0

            self.previous_time_fps = self.current_time
        # Reset i after every n frames
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


class FrameProcess(Process):
    """A basic class for a process that deals with frames. It provides
    framerate calculation.

    Parameters
    ----------
        n_fps_frames:
            the maximal number of frames to use to calculate framerate

    Returns
    -------

    """

    def __init__(self, name="", n_fps_frames=10):
        super().__init__()
        self.name = name
        self.framerate_rec = FramerateRecorder(n_fps_frames=n_fps_frames)
        self.framerate_queue = Queue()
        self.message_queue = Queue()

    def update_framerate(self):
        self.framerate_rec.update_framerate()
        if self.framerate_rec.i_fps == 0:
            self.framerate_queue.put(
                (self.framerate_rec.current_time, self.framerate_rec.current_framerate)
            )


def prepare_json(it, **kwargs):
    """Used to create a dictionary which will be safe to put in MongoDB

    Parameters
    ----------
    it :
        the item which will be recursively sanitized
    **kwargs :
        convert_datetime: bool
            if datetiems are to be converted to strings for JSON serialization
        eliminate_df: bool
            remove dataframes from the dictionary

    Returns
    -------

    """
    safe_types = (int, float, str)

    for st in safe_types:
        if isinstance(it, st):
            return it
    if isinstance(it, dict):
        new_dict = dict()
        for key, value in it.items():
            new_dict[key] = prepare_json(value, **kwargs)
        return new_dict
    if isinstance(it, tuple):
        return tuple([prepare_json(el, **kwargs) for el in it])
    if isinstance(it, list):
        return [prepare_json(el, **kwargs) for el in it]
    if isinstance(it, np.generic):
        return np.asscalar(it)
    if isinstance(it, datetime):
        if kwargs.get("convert_datetime", False):
            return it.isoformat()
        else:
            temptime = time.mktime(it.timetuple())
            return datetime.utcfromtimestamp(temptime)
    if isinstance(it, pd.DataFrame):
        if kwargs.get("eliminate_df", False):
            return 0
        else:
            return it.to_dict("list")
    if isinstance(it, Path):
        return str(it)
    return 0


def get_default_args(func):
    """Find default arguments of functions

    Parameters
    ----------
    func :
        

    Returns
    -------

    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def strip_values(it):
    """

    Parameters
    ----------
    it :
        

    Returns
    -------

    """
    if isinstance(it, OrderedDict) or isinstance(it, dict):
        new_dict = dict()
        for key, value in it.items():
            if not key == "value":
                new_dict[key] = strip_values(value)
        return new_dict
    else:
        return it


def interpolate_nan(a):
    inds = np.arange(a.shape[0])
    finite = np.all(np.isfinite(a), 1)
    if np.sum(finite) < 2:
        return np.nan_to_num(a)
    f = interp1d(
        inds[finite], a[finite, :], axis=0, bounds_error=False, fill_value="extrapolate"
    )
    a[~finite, :] = f(inds[~finite])
    return a


def get_classes_from_module(input_module, parent_class):
    """Find all the classes in a module that are children of a parent one.

    Parameters
    ----------
    input_module :
        module object
    parent_class :
        parent class object

    Returns
    -------
    type
        OrderedDict of subclasses found

    """
    classes = inspect.getmembers(input_module, inspect.isclass)
    ls_classes = OrderedDict(
        {
            c[1].name: c[1]
            for c in classes
            if issubclass(c[1], parent_class) and not c[1] is parent_class
        }
    )

    return ls_classes


def recursive_update(d, u):
    """ Simple recursive update of dictionaries, from StackOverflow

    :param d: dict to update
    :param u: new values
    :return:
    """
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


@jit(nopython=True)
def reduce_to_pi(angle):
    """Puts an angle or array of angles inside the (-pi, pi) range"""
    return np.mod(angle + np.pi, 2 * np.pi) - np.pi


def save_df(df, path, fileformat):
    """ Saves the dataframe in one of the supported formats

    Parameters
    ----------
    df
    path
    fileformat

    Returns
    -------

    """
    outpath = Path(str(path) + "." + fileformat)
    if fileformat == "csv":
        # replace True and False in csv files:
        df.replace({True: 1, False: 0}).to_csv(str(outpath), sep=";")
    elif fileformat == "feather":
        df.to_feather(outpath)
    elif fileformat == "hdf5":
        df.to_hdf(outpath, "/data", complib="blosc", complevel=5)
    elif fileformat == "json":
        json.dump(df.to_dict(), open(str(outpath), "w"))
    else:
        raise (NotImplementedError(fileformat + " is not an implemented log format"))
    return outpath.name
