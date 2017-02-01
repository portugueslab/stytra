import datetime
import os

import deepdish as dd
import param

from stytra.paramqt import ParameterGui


class DataCollector:
    """
    Data collector class. You can throw here references for any kind of data
    and when prompted it saves their current value in the nice HDF5 metadata file
    ad maiorem dei gloriam.
    """

    # Metadata entries are categorized with a fixed dictionary:
    metadata_categories = dict(MetadataFish='fish',
                               MetadataLightsheet='imaging',
                               MetadataGeneral='general')

    def __init__(self, *data_tuples_list, folder_path=''):
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

        # Categories are initialized by default --> not sure of the inconveniences of
        # eventual void HDF5 categories
        self.data_dict = dict(fish={}, stimulus={}, imaging={}, behaviour={}, general={})

        # Check validity of directory:
        if os.path.isdir(folder_path):
            self.folder_path = folder_path
        else:
            print('The specified directory does not exist! \n '
                  '%s will be used' % (os.getcwd()))
        self.data_tuples = []

        for data_element in data_tuples_list:
            if isinstance(data_element, Metadata):
                self.add_data_source(data_element)
            else:
                self.add_data_source(*data_element)

    def add_data_source(self, *args):
        """
        Function for adding new data sources.
            - Metadata objects: can be passed without specifications
                                (e.g., add_data_source(MetadataFish()));
            - Dictionaries: must be preceded by the data category
                            (e.g., add_data_source('imaging', parameters_dict);
            - Single values: can be added in a tuple with category and name
                            (e.g., add_data_source('imaging', 'frequency', freq_value);
            -folder_path: destination of the HDF5 object

        At this point the value of the variables is not considered!
        """

        # just some control on the incoming data
        if len(args) == 1:
            try:
                assert isinstance(args[-1], Metadata)
            except AssertionError:
                print('Only Metadata objects can be passed without category')
        else:
            try:
                assert args[0] in self.data_dict.keys()
            except AssertionError:
                print('Unknown data category: ' + args[0])

            if len(args) < 3:
                try:
                    assert isinstance(args[-1], dict)
                except AssertionError:
                    print('Data of %s type must have an associated label!' % (type(args[-1])))
            else:
                try:
                    assert isinstance(args[1], str)
                except AssertionError:
                    print('Second argument must be a string!')

        self.data_tuples.append(args)

    def save(self):
        """
        Save the HDF5 file considering the current value of all the entries of the class
        """
        for data_entry in self.data_tuples:
            value = data_entry[-1]
            if isinstance(value, dict):
                category = data_entry[0]
                self.data_dict[category].update(value)
            elif isinstance(value, Metadata):
                category = DataCollector.metadata_categories[type(value).__name__]
                self.data_dict[category].update(value.get_param_dict())
            else:
                category = data_entry[0]
                label = data_entry[1]
                self.data_dict[category][label] = value

        # HDF5 are saved as timestamped Ymd_HMS_metadata.h5 files:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_metadata")
        filename = self.folder_path + timestamp + '.h5'
        dd.io.save(filename, self.data_dict)


class Metadata(param.Parameterized):
    """General metadata class
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gui = ParameterGui(metadata_obj=self)

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
        self.gui = ParameterGui(metadata_obj=self)
        self.gui.show()


class MetadataFish(Metadata):
    """Fish description metadata class
    """
    fish_age_days = param.Integer(default=6, bounds=(2, 9))
    fish_genotype = param.ObjectSelector(default='TL',
                                         objects=['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                                                  'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                                                  'Fyn-tagRFP:PC:NLS-6s', 'Fyn-tagRFP:PC'],
                                         check_on_set=False)
    fish_comments = param.String()


class MetadataLightsheet(Metadata):
    """Lightsheet imaging description metadata class
    """
    imaging_type = param.String(default='lightsheet', constant=True)
    frame_rate_hz = param.Number(default=20, bounds=(1., 200.))
    piezo_frequency_hz = param.Number(default=5, bounds=(0., 10))
    piezo_amplitude = param.Number(default=0, bounds=(0., 10))
    exposure_time_ms = param.Number(default=1, bounds=(0.1, 10))
    laser_power_mA = param.Number(default=23, bounds=(0.1, 100))
    scanning_profile = param.ObjectSelector(default='sawtooth', objects=['none', 'sawtooth', 'triangle'])
    binning = param.ObjectSelector(default='2x2', objects=['1x1', '2x2', '4x4'])
    trigger = param.ObjectSelector(default='External', objects=['Internal', 'External'])

class MetadataCamera(Metadata):
    exposure = param.Number(default= 20.0, bounds =[0.5, 50], doc='Exposure in milliseconds')
    gain = param.Number(default=1.0, bounds = [0.1, 3], doc='Camera amplification gain')


class MetadataGeneral(Metadata):
    """Fish description metadata class
    """
    experiment_name = param.String()
    experimenter_name = param.String()
