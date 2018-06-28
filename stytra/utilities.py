import datetime
import time
from collections import OrderedDict
from multiprocessing import Process
from datetime import datetime

import numpy as np
import pandas as pd
import inspect

from pyqtgraph.parametertree import Parameter


class Database:
    """ """

    def __init__(self):
        pass

    def add_experiment(self, exp):
        """

        Parameters
        ----------
        exp :
            

        Returns
        -------

        """
        pass


class FrameProcess(Process):
    """A basic class for a process that deals with frames. It provides
    framerate calculation.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self, n_fps_frames=10, print_framerate=False):
        """ Initialize the class.
        :param n_fps_frames: number of frames after which framerate is updated.
        :param print_framerate: flag for printing framerate
        """
        super().__init__()

        # Set framerate calculation parameters
        self.n_fps_frames = n_fps_frames
        self.i_fps = 0
        self.previous_time_fps = None
        self.current_framerate = None
        self.print_framerate = print_framerate

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
                if self.print_framerate:
                    print("FPS: " + str(self.current_framerate))

            self.previous_time_fps = self.current_time
        # Reset i after every n frames
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


def prepare_json(it, **kwargs):
    """Used to create a dictionary which will be safe to put in MongoDB

    Parameters
    ----------
    it :
        the item which will be recursively sanitized
    **kwargs :
        

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
        tuple_out = tuple([prepare_json(el, **kwargs) for el in it])
        if (
            len(tuple_out) == 2
            and kwargs.get("paramstree", False)
            and isinstance(tuple_out[1], dict)
        ):
            if len(tuple_out[1]) == 0:
                return tuple_out[0]
            else:
                return tuple_out[1]
        else:
            return tuple_out
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


class HasPyQtGraphParams:
    """This class is used to have a number of objects (experiment interfaces and
    protocols) sharing a global pyqtgraph Parameter object that will be used
    for saving data_log and restoring the app to the last used state.
    _params is a class attribute and is shared among all subclasses; each
    subclass will have an alias, params, providing access to its private

    Parameters
    ----------

    Returns
    -------

    """
    _params = Parameter.create(name="global_params", type="group")

    def __init__(self, name=None):
        """ Create the params of the instance and add it to the global _params
        of the class. If the name passed already exists in the tree, it will be
        overwritten.
        :param name: Name for the tree branch where this parameters are stored.
                     If nothing is passed, child class name will be used.
        """

        if name is None:
            name = self.__class__.__name__

        self.params = Parameter.create(name=name, type="group")

        existing_children = self._params.children()

        # WARNING!!
        # Here there can be undesired emissions of the StateChanged signal!
        # If you are removing a child params, it will emit a signal you have
        # to block.
        for child in existing_children:
            if child.name() == name:
                self._params.removeChild(child)

        self._params.addChild(self.params)

    def add_params(self, **kwargs):
        """Sets new parameters with keys and default values
        or the full param specification

        Parameters
        ----------
        kwargs :
            new parameters to add
        **kwargs :
            

        Returns
        -------
        type
            None

        """
        for name, value in kwargs.items():
            self.add_one_param(name, value)

    def add_one_param(self, name, value, get_var_type=True):
        """Easy set for adding parameters.

        Parameters
        ----------
        name :
            name of new parameter
        value :
            either a value entry or a dictionary of valid keys
            for a parameter (e.g. type, visible, editable, etc.)
        get_var_type :
            if True, value type will be set as parameter type (Default value = True)

        Returns
        -------

        """
        if isinstance(value, dict):  # Allows passing dictionaries:
            entry_dict = {"name": name}  # add name
            entry_dict.update(value)
            self.params.addChild(entry_dict)
        else:
            if get_var_type:  # if specification of type is required, infer it
                self.params.addChild(
                    {"name": name, "value": value, "type": type(value).__name__}
                )
            else:
                self.params.addChild({"name": name, "value": value})

    def update_params(self, **kwargs):
        """ Updates the parameters from a kwargs

        :param kwargs:
        :return:
        """
        for key, value in kwargs:
            self.params[key] = value

    def get_clean_values(self):
        """ """
        return prepare_json(self.params.getValues(), paramstree=True)


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
