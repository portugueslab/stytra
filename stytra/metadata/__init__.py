import param
from paramqt import ParameterGui


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

    age = param.Integer(default=6, bounds=(2, 14), doc='Fish age (days)')
    genotype = param.ObjectSelector(default='TL',
                                         objects=['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                                                  'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                                                  'Fyn-tagRFP:PC:NLS-6s', 'Fyn-tagRFP:PC',
                                                  'Aldoca:Gal4;UAS:GFP+mnn:Gal4;UAS:GFP',
                                                  'PC:epNtr-tagRFP',
                                                  'NeuroD-6f'],
                                         check_on_set=False)
    dish_diameter = param.ObjectSelector(default='60',
                                         objects=['0', '30', '60', '90',
                                                  'lightsheet'])
    embedded = param.Boolean(default=True)
    treatment = param.ObjectSelector(default='', objects=['',
                                                          '10mM MTz',
                                                          'Bungarotoxin'], check_on_set=False)
    screened = param.ObjectSelector(default='not', objects=['not', 'dark', 'bright'])
    comments = param.String()


class MetadataCamera(Metadata):
    category = 'camera'

    exposure = param.Number(default=1, bounds=[0.1, 50], doc='Exposure (ms)')
    # framerate = param.Number(default=100, bounds=[0.5, 1000], doc='Frame rate (Hz)')
    gain = param.Number(default=1.0, bounds=[0.1, 3], doc='Camera amplification gain')


class MetadataGeneral(Metadata):
    """General experiment properties metadata class
    """
    category = 'general'

    experiment_name = param.String()
    experimenter_name = param.ObjectSelector(default='Vilim Stih',
                                             objects=['Elena Dragomir',
                                                      'Andreas Kist',
                                                      'Laura Knogler',
                                                      'Daniil Markov',
                                                      'Pablo Oteiza',
                                                      'Virginia Palieri',
                                                      'Luigi Petrucco',
                                                      'Ruben Portugues',
                                                      'Vilim Stih',
                                                      'Tugce Yildizoglu'
                                                      ])

    setup_name = param.ObjectSelector(default='Saskin', objects=['2p',
                                               'Lightsheet',
                                               '42',
                                               'Saskin',
                                               'Archimedes',
                                               'Helmut',
                                               'Katysha'])

