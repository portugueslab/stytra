import datetime
import os

import deepdish as dd
import numpy as np
import pandas as pd
import param

from stytra.metadata import Metadata


class Accumulator:
    """ A general class for an object that accumulates that
    will be saved or plotted in real time

    """
    def __init__(self):
        self.stored_data = []
        self.header_list = ['time']
        self.starting_time = datetime.datetime.now()

    def get_dataframe(self):
        """Returns pandas DataFrame with data and headers
        """
        data_array = pd.lib.to_object_array(self.stored_data).astype(np.float64)
        return pd.DataFrame(data_array[:, :len(self.header_list)],
                            columns=self.header_list)

    def get_last_n(self, n):
        last_n = min(n, len(self.stored_data))
        data_list = self.stored_data[-max(last_n, 1):]

        obar = np.array(data_list)
        return obar


def metadata_dataframe(metadata_dict, time_step=0.005):
    """
    Function for converting a metadata dictionary into a pandas dataframe
    for saving
    :param metadata_dict: metadata dictionary (containing stimulus log!)
    :param time_step: time step (used only if tracking is not present!)
    :return: a pandas DataFrame with a 'stimulus' column for the stimulus
    """

    # Check if tail tracking is present, to use tracking dataframe as template.
    # If there is no tracking, generate a dataframe with time steps specified:
    if 'tail_tracking' in metadata_dict['behaviour'].keys():
        final_df = metadata_dict['behaviour']['tail_tracking'].copy()
    else:
        t = metadata_dict['stimulus']['log'][-1]['t_stop']
        timearr = np.arange(0, t, time_step)
        final_df = pd.DataFrame(timearr, columns=['time'])

    # Control for delays between tracking and stimulus starting points:
    delta_time = 0
    if 'tail_tracking_start' in metadata_dict['behaviour'].keys():
        stim_start = metadata_dict['stimulus']['log'][0]['started']
        track_start = metadata_dict['behaviour']['tail_tracking_start']
        delta_time = (stim_start - track_start).total_seconds()

    # Assign in a loop a stimulus to each time point
    start_point = None
    for stimulus in metadata_dict['stimulus']['log']:
        if stimulus['name'] == 'start_acquisition':
            start_point = stimulus

        final_df.loc[(final_df['time'] > stimulus['t_start'] + delta_time) &
                     (final_df['time'] < stimulus['t_stop'] + delta_time),
                     'stimulus'] = str(stimulus['name'])

    # Check for the 'start acquisition' which run for a very short time and can be
    # missed:
    if start_point:
        start_idx = np.argmin(abs(final_df['time'] - start_point['t_start']))
        final_df.loc[start_idx, 'stimulus'] = 'start_acquisition'

    return final_df


class DataCollector:
    """
    Data collector class. You can throw here references for any kind of data
    and when prompted it saves their current value in the nice HDF5 metadata file
    ad maiorem dei gloriam.
    """

    # Categories are hardwired, to control integrity of the output HDF5 file
    data_dict_template = dict(fish={}, stimulus={}, imaging={},
                              behaviour={}, general={}, camera={},
                              tracking={})

    def __init__(self, *data_tuples_list, folder_path='./', use_last_val=True):
        """
        Init function.
            - Metadata objects: can be added without specifications
                                (e.g., DataCollector(MetadataFish()))
            - Dictionaries: can be added in a tuple with the category
                            (e.g., DataCollector(('imaging', parameters_dict))
            - Single entries: can be added in a tuple with category and name
                              (e.g., DataCollector(('imaging', 'frequency', freq_value))
            -folder_path: destination of the HDF5 object

        If more entries want to save data in the same destination of the HDF5
        final file, the last of the two added to the DataCollector object will
        overwrite the other.
        """

        # Check validity of directory:
        if os.path.isdir(folder_path):
            if not folder_path.endswith('/'):
                folder_path += '/'
            self.folder_path = folder_path
        else:
            raise ValueError('The specified directory does not exist!')

        # Try to find previously saved metadata:
        self.last_metadata = None
        list_metadata = sorted([fn for fn in os.listdir(folder_path) if fn.endswith('metadata.h5')])
        if len(list_metadata) > 0:
            self.last_metadata = dd.io.load(folder_path + list_metadata[-1])

        self.data_tuples = []

        # Add all the data tuples provided upon instantiation:
        for data_element in data_tuples_list:
            if isinstance(data_element, Metadata):
                self.add_data_source(data_element, use_last_val=use_last_val)
            else:
                self.add_data_source(*data_element, use_last_val=use_last_val)

    def add_data_source(self, *args, use_last_val=True):
        """
        Function for adding new data sources.
            - Metadata objects: can be passed without specifications
                                (e.g., add_data_source(MetadataFish()));
            - Dictionaries: must be preceded by the data category
                            (e.g., add_data_source('imaging', parameters_dict);
            - Single values: can be added in a tuple with category and name
                            (e.g., add_data_source('imaging', 'frequency', freq_value);
            - Object attributes: can be added in a tuple with category, name, object and entry
                            (e.g., add_data_source('stimulus', 'log', protocol_obj, 'log')
            -folder_path: destination of the HDF5 object

        At this point the value of the variables is not considered!
        The set_to_last_value method can be used for restoring values from previous
        sessions.
        """
        # The single values entry may be dismissed?

        # If true, use the last values used for this parameter
        if use_last_val:
            self.set_to_last_value(*args)

        # just some control on the incoming data
        if len(args) == 1:  # parameterized objects don't need a category
            if not isinstance(args[-1], Metadata):
                ValueError('Only Metadata objects can be passed without category!')

        if len(args) > 1:  # check validity of category value
            if not isinstance(args[0], str):
                ValueError('First argument must be a string with the category!')

            if not args[0] in DataCollector.data_dict_template.keys():
                ValueError('Unknown data category: ' + args[0])

            if len(args) == 2:  # only dictionaries can have 2 args
                if not isinstance(args[-1], dict):
                    ValueError('Only dictionaries can be passed without an entry name!')

        if len(args) > 2:
            if not isinstance(args[1], str):
                ValueError('Second argument must be a string with the entry name!')

        if len(args) > 3:
            if isinstance(args[2], dict):
                if not args[3] in args[2].keys():
                    ValueError('Fourth argument must be a key of the third!')
            elif hasattr(args[2], args[3]):
                    ValueError('Fourth argument must be an attribute of the third!')

        if len(args) > 4:
            ValueError('Too many arguments!')

        self.data_tuples.append(args)

    def get_full_dict(self):
        data_dict = DataCollector.data_dict_template

        for data_entry in self.data_tuples:
            if isinstance(data_entry[-1], dict):  # dictionaries;
                category = data_entry[0]
                data_dict[category].update(data_entry[-1])

            elif isinstance(data_entry[-1], Metadata):  # parameterized objects;
                category = data_entry[-1].category
                data_dict[category].update(data_entry[-1].get_param_dict())

            if len(data_entry) > 2:
                category = data_entry[0]
                label = data_entry[1]
                if len(data_entry) == 3: # single value entries;
                    data_dict[category][label] = data_entry[2]

                elif len(data_entry) == 4: # dict value entries;
                    if isinstance(data_entry[2], dict):
                        data_dict[category][label] = data_entry[2][data_entry[3]]
                    else: # object attribute entries
                        data_dict[category][label] = getattr(data_entry[2], data_entry[3])

        return data_dict

    def save(self, timestamp=None, save_csv=True):
        """
        Save the HDF5 file considering the current value of all the entries of the class
        """

        data_dict = self.get_full_dict()

        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # HDF5 are saved as timestamped Ymd_HMS_metadata.h5 files:
        filename = self.folder_path + timestamp + '_metadata.h5'

        dd.io.save(filename, data_dict)
        print('saved '+filename)
        # Save .csv file if required
        if save_csv:
            filename_df = self.folder_path + timestamp + '_metadata_df.csv'
            dataframe = metadata_dataframe(data_dict)
            dataframe.to_csv(filename_df)

    def set_to_last_value(self, *args):
        """
        This function take arguments as the add_data_source function;
        Then, if possible, it sets the value of all the referenced variables
        to the corresponding value stored in the dictionary.
        This is not possible for single value entries, and it will be applied
        only for dictionaries, parameterized objects and attributes.
        """
        # It is a little bit messy. It may be made cleaner (?).

        if self.last_metadata:
            if not isinstance(args[-1], list): # avoid logs #TODO make logs pd DataFrame

                if isinstance(args[-1], dict):  # dictionaries
                    category = args[0]
                    for key_new_dict in args[-1].keys():
                        if key_new_dict in self.last_metadata[category].keys():
                            args[-1][key_new_dict] = self.last_metadata[category][key_new_dict]

                elif isinstance(args[-1], Metadata):  # parameterized objects
                    category = args[-1].category
                    for key_new_obj in args[-1].get_param_dict().keys():
                        param_obj = args[-1].params()[key_new_obj]

                        if not param_obj.constant:  # leave eventual constant values
                            if key_new_obj in self.last_metadata[category].keys():  # check if stored
                                old_entry = self.last_metadata[category][key_new_obj]
                                if isinstance(param_obj, param.Integer):
                                    old_entry = int(old_entry)
                                elif isinstance(param_obj, param.String):
                                    old_entry = str(old_entry)

                                setattr(args[-1], key_new_obj, old_entry)

                elif len(args) == 4:  # dict entries and objects attributes
                    category = args[0]
                    label = args[1]
                    if label in self.last_metadata[category].keys():  # dict
                        if isinstance(args[2], dict):
                            args[2][args[3]] = self.last_metadata[category][label]
                        else:  # attribute
                            setattr(args[2], args[3], self.last_metadata[category][label])