import datetime
import os

import deepdish as dd
import numpy as np
import pandas as pd
import param
import json

# from stytra.metadata import Metadata
from copy import deepcopy
from pyqtgraph.parametertree import Parameter, ParameterTree
from stytra.dbconn import sanitize_item


class HasPyQtGraphParams(object):
    """
    This class is used to have a number of objects which
    constitute the experiment interfaces and protocols sharing a global
    pyqtgraph Parameter object that will be used for saving metadata and
    restoring the app to the last used data.
    _params is a class attribute and is shared among all subclasses; each
    subclass will have an alias, params, providing access to its private
    parameters.
    """
    _params = Parameter.create(name='global_params', type='group')

    def __init__(self, name=None):
        # Here passing the name for the new branch allows the user to easily
        # overwrite branches of the parameter tree. If not passed,
        # children class name will be used.

        if name is None:
            name = self.__class__.__name__
        self.params = Parameter.create(name=name,
                                       type='group')

        existing_children = self._params.children()

        for child in existing_children:
            if child.name() == name:
                self._params.removeChild(child)
        self._params.addChild(self.params)

    def set_new_param(self, name, value, get_var_type=True):
        """ Easy set for new parameters
        :param name: name of new parameter
        :param value: either a value entry or a dictionary of valid keys
                      for a parameter (e.g. type, visible, editable, etc.)
        :param get_var_type: if True, value type will be set as parameter type
        :return:
        """
        if isinstance(value, dict):  # Allows passing dictionaries:
            entry_dict = {'name': name}  # add name
            entry_dict.update(value)
            self.params.addChild(entry_dict)
        else:
            if get_var_type:  # if specification of type is required, infer it
                self.params.addChild({'name': name, 'value': value,
                                      'type': type(value).__name__})
            else:
                self.params.addChild({'name': name, 'value': value})

    def get_clean_values(self):
        return sanitize_item(self.params.getValues(), paramstree=True)


class GuiMetadata(HasPyQtGraphParams):
    def __init__(self):
        super().__init__()
        self.protocol_params_tree = ParameterTree(showHeader=False)

    def get_param_dict(self):
        return self.params.getValues()

    def show_metadata_gui(self):
        self.protocol_params_tree.setParameters(self.params)
        self.protocol_params_tree.setWindowTitle('Metadata')
        self.protocol_params_tree.resize(450, 600)
        return self.protocol_params_tree

    def get_state(self):
        return self._params.saveState()

    def restore_state(self):
        pass


class GeneralMetadata(GuiMetadata):
    def __init__(self):
        super().__init__()
        params =[
                dict(name='session_id', type='int', value=0),
                {'name': 'experimenter_name', 'type': 'list', 'value':
                    'Vilim Stih',
                 'values': ['Elena Dragomir',
                            'Andreas Kist',
                            'Laura Knogler',
                            'Daniil Markov',
                            'Pablo Oteiza',
                            'Virginia Palieri',
                            'Luigi Petrucco',
                            'Ruben Portugues',
                            'Vilim Stih',
                            'Tugce Yildizoglu'],
                 },
                {'name': 'setup_name',  'type': 'list',
                 'values': ['2p',
                            'Lightsheet',
                            '42',
                            'Saskin',
                            'Archimedes',
                            'Helmut',
                            'Katysha'], 'value': 'Saskin'}]

        self.params.setName('general_metadata')
        self.params.addChildren(params)


class FishMetadata(GuiMetadata):
    def __init__(self):
        super().__init__()
        params = [
                  dict(name='id', type='int', value=0),
                {'name': 'age', 'type': 'int', 'value': 7, 'limits': (4, 20),
                 'tip': 'Fish age', 'suffix': ' dpf'},
                {'name': 'genotype', 'type': 'list',
                 'values': ['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                            'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                            'Fyn-tagRFP:PC:NLS-6s', 'Fyn-tagRFP:PC',
                            'Aldoca:Gal4;UAS:GFP+mnn:Gal4;UAS:GFP',
                            'PC:epNtr-tagRFP',
                            'NeuroD-6f',
                            '152:Gal4;UAS:GCaMP6s',
                            '156:Gal4;UAS:GCaMP6s'], 'value': 'TL'},
                {'name': 'dish_diameter', 'type': 'list',
                 'values': ['0', '30', '60', '90', 'lightsheet'],
                 'value': '60'},

                {'name': 'comments', 'type': 'str', 'value': ""},
                {'name': 'embedded', 'type': 'bool', 'value': True,
                 'tip': "This is a checkbox"},
                {'name': 'treatment', 'type': 'list',
                 'values': ['',
                            '10mM MTz',
                            'Bungarotoxin'], 'value': ''},
                {'name': 'screened', 'type': 'list',
                 'values': ['not', 'dark', 'bright'], 'value': 'not'}]
        self.params.setName('fish_metadata')
        self.params.addChildren(params)


class Accumulator:
    """ A general class for an object that accumulates what
    will be saved or plotted in real time
    """
    def __init__(self, fps_range=10):
        self.stored_data = []
        self.header_list = ['t']
        self.starting_time = None
        self.fps_range = fps_range

    def reset(self, header_list=None):
        if header_list is not None:
            self.header_list = ['t'] + header_list
        self.stored_data = []
        self.starting_time = None

    def check_start(self):
        if self.starting_time is None:
            self.starting_time = datetime.datetime.now()

    def get_dataframe(self):
        """ Returns pandas DataFrame with data and headers
        """
        return pd.DataFrame(self.stored_data,
                            columns=self.header_list)

    def get_fps(self):
        try:
            last_t = self.stored_data[-1][0]
            t_minus_dif = self.stored_data[-self.fps_range][0]
            return self.fps_range/(last_t-t_minus_dif)
        except (IndexError, ValueError):
            return 0.0

    def get_last_n(self, n):
        last_n = min(n, len(self.stored_data))
        if len(self.stored_data) == 0:
            return np.zeros(len(self.header_list)).reshape(1, len(self.header_list))
        data_list = self.stored_data[-max(last_n, 1):]

        obar = np.array(data_list)
        return obar

    def get_last_t(self, t):
        n = int(self.get_fps()*t)
        return self.get_last_n(n)



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
    if 'tail' in metadata_dict['behaviour'].keys():
        final_df = metadata_dict['behaviour']['tail'].copy()
    else:
        t = metadata_dict['stimulus']['log'][-1]['t_stop']
        timearr = np.arange(0, t, time_step)
        final_df = pd.DataFrame(timearr, columns=['t'])

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

        final_df.loc[(final_df['t'] > stimulus['t_start'] + delta_time) &
                     (final_df['t'] < stimulus['t_stop'] + delta_time),
                     'stimulus'] = str(stimulus['name'])

    # Check for the 'start acquisition' which run for a very short time and can be
    # missed:
    if start_point:
        start_idx = np.argmin(abs(final_df['t'] - start_point['t_start']))
        final_df.loc[start_idx, 'stimulus'] = 'start_acquisition'

    return final_df


class DataCollector:
    def __init__(self, *data_tuples_list, folder_path='./'):
        """ It accept static data in a HasPyQtGraph class, which will be
        restored to the last values, or dynamic data like tail tracking or
        stimulus log that will not be restored.
        :param data_tuples_list: tuple of data to be added
        :param folder_path: destination for the final HDF5 object
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
        list_metadata = sorted([fn for fn in os.listdir(folder_path) if
                                fn.endswith('config.h5')])

        if len(list_metadata) > 0:
            self.last_metadata = \
                dd.io.load(folder_path + list_metadata[-1])

        self.log_data_dict = dict()
        self.static_metadata = None
        # Add all the data tuples provided upon instantiation:
        for data_element in data_tuples_list:
            self.add_data_source(*data_element)

    def restore_from_saved(self):
        if self.last_metadata is not None:
            self.static_metadata._params.restoreState(self.last_metadata)

    def add_data_source(self, entry, name='unspecified_entry'):
        """
        Function for adding new data sources. entry can fall under two cases:
            - Metadata object: will be used to get all the parameters from
                               HasPyQtGraphParams children
            - Log data, for stimulus log or tail tracking, or in general
                        inputs that are not reset from saved data
        """

        # If true, use the last values used for this parameter
        if isinstance(entry, HasPyQtGraphParams):
            self.static_metadata = entry
            self.restore_from_saved()

        else:
            self.log_data_dict[name] = entry

    def get_full_dict(self):
        data_dict = dict()
        data_dict['log_data'] = self.log_data_dict
        data_dict['static_metadata'] = self.static_metadata._params.saveState()
        return data_dict

    def get_clean_dict(self, paramstree=True, eliminate_df=False,
                       convert_datetime=False):
        clean_data_dict = dict(fish={}, stimulus={}, imaging={},
                               behaviour={}, general={}, camera={},
                               tracking={}, unassigned={})

        # Static metadata:
        value_dict = deepcopy(self.static_metadata._params.getValues())

        # Logs:
        value_dict.update(deepcopy(self.log_data_dict))

        for key in value_dict.keys():
            category = key.split('_')[0]
            value = sanitize_item(value_dict[key], paramstree=paramstree,
                                  convert_datetime=convert_datetime,
                                  eliminate_df=eliminate_df)
            if category in clean_data_dict.keys():
                split_name = key.split('_')
                if split_name[1] == 'metadata':
                    clean_data_dict[category] = value
                else:
                    clean_data_dict[category]['_'.join(split_name[1:])] = value
            else:
                clean_data_dict['unassigned'][key] = value

        return clean_data_dict

    def get_last(self, class_param_key):
        if self.last_metadata is not None:
            # TODO This is atrocious.
            return self.last_metadata['children'][class_param_key]['children']['name']['value']
        else:
            return None

    def save_config(self):
        data_dict = deepcopy(self.get_full_dict())
        dd.io.save(self.folder_path + 'config.h5', data_dict['static_metadata'])

    def save_log(self,  timestamp=None,):
        clean_dict = self.get_clean_dict(convert_datetime=True)
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save clean json file as timestamped Ymd_HMS_metadata.h5 files:
        print(str(clean_dict['fish']))
        fish_name = datetime.datetime.now().strftime("%y%m%d") + '_f' + str(clean_dict['fish']['id'])
        dirname = '/'.join([self.folder_path,
                   clean_dict['stimulus']['protocol_params']['name'],
                             fish_name,
                             str(clean_dict['general']['session_id'])])
        # dd.io.save(filename, self.get_clean_dict(convert_datetime=True))
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        with open(dirname+'/'+timestamp+'_metadata.json', 'w') as outfile:
            json.dump(clean_dict,
                      outfile, sort_keys=True)

    def save(self, timestamp=None):
        """
        Save the HDF5 file considering the current value of all the entries
        of the class
        """

        self.save_log(timestamp)
        self.save_config()
