import param
import deepdish as dd
import datetime


class DataCollector:
    """Data collector class.
    This class parse data and metadata about stimulation, behaviour, etc. and
    save everything in  a single HDF5 file
    """
    def __init__(self, *list_meta_objects):
        """

        :param list_meta_objects:
        """
        self.dict_meta_objects = dict()
        for meta_object in list_meta_objects:
            self.dict_meta_objects[type(meta_object).__name__] = meta_object

    def save_metadata(self, path_folder=''):
        dict_for_saving=dict()
        for meta_object in self.dict_meta_objects:
            dict_for_saving[meta_object] = self.dict_meta_objects[meta_object].get_param_dict()

        print(dict_for_saving)
        timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S_metadata")
        filename = path_folder + timestamp + '.h5'
        dd.io.save(filename, dict_for_saving)

    def add_metadata(self):
        pass



class Metadata(param.Parameterized):
    """General metadata class
    """
    def get_param_dict(self):
        tuple_list = dict(self.get_param_values())
        tuple_list.pop('name')
        return tuple_list


class MetadataFish(Metadata):
    """Fish description metadata class
        """
    fish_age = param.Integer(default=6, bounds=(3, 7))
    fish_genotype = param.ObjectSelector(default='TL', objects=['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                                                        'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                                                        'Fyn-tagRFP:PC:NLS-6s','Fyn-tagRFP:PC'], check_on_set=False)
    fish_comments = param.String()


class MetadataLightsheet(Metadata):
    """Lightsheet imaging description metadata class
    """
    frame_rate = param.Number(default=20, bounds=(1., 200.))
    piezo_frequency = param.Number(default=0, bounds=(0., 10))
    exposure_time_ms = param.Number(default=1, bounds=(0.1, 10))
    laser_power_mA = param.Number(default=23, bounds=(0.1, 100))
    scanning_profile = param.ObjectSelector(default='sawtooth', objects=['none', 'sawtooth', 'triangle'])
    binning = param.ObjectSelector(default='2x2', objects=['1x1', '2x2', '4x4'])
    trigger = param.ObjectSelector(default='External', objects=['Internal', 'External'])


if __name__ == '__main__':
    meta_collector_obj = DataCollector(MetadataFish(), MetadataLightsheet())
    meta_collector_obj.save_metadata()




