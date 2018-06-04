import datetime
import time
from multiprocessing import Process
from datetime import datetime

import numpy as np
import pandas as pd


class FrameProcessor(Process):
    """ A basic class for a process that deals with frames. It provides
    framerate calculation.
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
        """ Calculate the framerate every n_fps_frames frames.
        """
        # If number of frames for updating is reached:
        if self.i_fps == self.n_fps_frames - 1:
            self.current_time = datetime.now()
            if self.previous_time_fps is not None:
                try:
                    self.current_framerate = self.n_fps_frames / (
                        self.current_time - self.previous_time_fps).total_seconds()
                except ZeroDivisionError:
                    self.current_framerate = 0
                if self.print_framerate:
                    print('FPS: ' + str(self.current_framerate))

            self.previous_time_fps = self.current_time
        # Reset i after every n frames
        self.i_fps = (self.i_fps + 1) % self.n_fps_frames


def prepare_json(it, **kwargs):
    """ Used to create a dictionary which will be safe to put in MongoDB

    :param it: the item which will be recursively sanitized
    :return:
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
        tuple_out = tuple([prepare_json(el, **kwargs)
                           for el in it])
        if len(tuple_out) == 2 and kwargs.get('paramstree', False) and \
                isinstance(tuple_out[1], dict):
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
    if isinstance(it, datetime.datetime):
        if kwargs.get("convert_datetime", False):
            return it.isoformat()
        else:
            temptime = time.mktime(it.timetuple())
            return datetime.datetime.utcfromtimestamp(temptime)
    if isinstance(it, pd.DataFrame):
        if kwargs.get("eliminate_df", False):
            return 0
        else:
            return it.to_dict('list')
    return 0