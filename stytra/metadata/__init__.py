import datetime
import os

import deepdish as dd
import param

from paramqt import ParameterGui


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

    def __init__(self, *data_tuples_list, folder_path='./'):
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
                self.add_data_source(data_element)
            else:
                self.add_data_source(*data_element)

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

    def save(self, timestamp=None):
        """
        Save the HDF5 file considering the current value of all the entries of the class
        """

        data_dict = self.get_full_dict()

        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # HDF5 are saved as timestamped Ymd_HMS_metadata.h5 files:
        filename = self.folder_path + timestamp + '_metadata.h5'
        print(filename)
        dd.io.save(filename, data_dict)

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


class Metadata(param.Parameterized):
    """General metadata class
    """
    category = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gui = None  # avoid unnecessary Qwidgets around

    def get_param_dict(self):
        tuple_list = dict(self.get_param_values())
        tuple_list.pop('name')
        return tuple_list

    def set_fix_value(self, obj, val):
        """
        Set a new value and make it non-modifiable
        (e.g., for parameters read from the setup)
        """
        setattr(self, obj, val)
        setattr(self.params(obj), 'constant', True)

    def show_gui(self):
        self.gui = self.get_gui(self)
        self.gui.show()

    def get_gui(self, save_button=True):
        return ParameterGui(metadata_obj=self, save_button=save_button)


class MetadataFish(Metadata):
    """Fish description metadata class
    """
    category = 'fish'

    fish_age = param.Integer(default=6, bounds=(2, 9), doc='Fish age (days)')
    fish_genotype = param.ObjectSelector(default='TL',
                                         objects=['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                                                  'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                                                  'Fyn-tagRFP:PC:NLS-6s', 'Fyn-tagRFP:PC'],
                                         check_on_set=False)
    fish_comments = param.String()


class MetadataLightsheet(Metadata):
    """Lightsheet imaging description metadata class
    """
    category = 'imaging'

    imaging_type = param.String(default='lightsheet', constant=True)
    frame_rate = param.Number(default=20, bounds=(1., 200.), doc='Camera frame rate (Hz)')
    piezo_frequency = param.Number(default=5, bounds=(0., 10), doc='Scanning frequency (Hz)')
    piezo_amplitude = param.Number(default=0, bounds=(0., 10), doc='Piezo scanning amplitude (arbitrary voltage)')
    exposure_time = param.Number(default=1, bounds=(0.1, 10), doc='Exposure (ms)')
    laser_power = param.Number(default=23, bounds=(0.1, 100), doc='Laser power (mA)')
    scanning_profile = param.ObjectSelector(default='sawtooth', objects=['none', 'sawtooth', 'triangle'])
    binning = param.ObjectSelector(default='2x2', objects=['1x1', '2x2', '4x4'])
    trigger = param.ObjectSelector(default='External', objects=['Internal', 'External'])


class MetadataCamera(Metadata):
    category = 'camera'

    exposure = param.Number(default=2, bounds=[0.1, 50], doc='Exposure (ms)')
    framerate = param.Number(default=500, bounds=[0.5, 1000], doc='Frame rate (Hz)')
    gain = param.Number(default=1.0, bounds=[0.1, 3], doc='Camera amplification gain')


class MetadataGeneral(Metadata):
    """General experiment properties metadata class
    """
    category = 'general'

    experiment_name = param.String()
    experimenter_name = param.String()
