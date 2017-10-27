import param
from paramqt import ParameterGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from stytra.collectors import HasPyQtGraphParams


class Metadata(HasPyQtGraphParams):
    def __init__(self):
        self.gui = None  # avoid unnecessary Qwidgets around

        params = [
            {'name': 'fish_metadata', 'type': 'group', 'children': [
                {'name': 'age', 'type': 'int', 'value': 7, 'limits': (7, 15), 'tip': 'Fish age (days)'},
                {'name': 'genotype', 'type': 'list',
                 'values': ['TL', 'Huc:GCaMP6f', 'Huc:GCaMP6s',
                            'Huc:H2B-GCaMP6s', 'Fyn-tagRFP:PC:NLS-6f',
                            'Fyn-tagRFP:PC:NLS-6s', 'Fyn-tagRFP:PC',
                            'Aldoca:Gal4;UAS:GFP+mnn:Gal4;UAS:GFP',
                            'PC:epNtr-tagRFP',
                            'NeuroD-6f'], 'value': 'TL'},
                {'name': 'dish_diameter', 'type': 'list',
                 'values': ['0', '30', '60', '90', 'lightsheet'], 'value': '60'},

                {'name': 'comments', 'type': 'str', 'value': ""},
                {'name': 'embedded', 'type': 'bool', 'value': True, 'tip': "This is a checkbox"},
                {'name': 'treatment', 'type': 'list',
                 'values': ['',
                            '10mM MTz',
                            'Bungarotoxin'], 'value': ''},
                {'name': 'screened', 'type': 'list',
                 'values': ['not', 'dark', 'bright'], 'value': 'not'}]},

            {'name': 'general_metadata', 'type': 'group', 'visible': True,
             'children': [
                {'name': 'experiment_name', 'type': 'str', 'value': ''},
                {'name': 'experimenter_name', 'type': 'list', 'value': 'Vilim Stih',
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
             }


            ]

        self.params.setName('general_metadata')
        self.params.addChildren(params)

    def get_param_dict(self):
        return self.params.getValues()

    def show_gui(self):
        self.gui = self.get_gui(self)
        self.gui.show()

    def get_gui(self):
        t = ParameterTree()
        t.setParameters(self.params, showTop=False)
        t.setWindowTitle('pyqtgraph example: Parameter Tree')
        return t

    def get_state(self):
        return self.params.saveState()

    def restore_state(self):
        pass
#
#
# class MetadataGeneral(param.Parameterized):
#     """General metadata class
#     """
#     category = None
#
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.gui = None  # avoid unnecessary Qwidgets around
#
#     def get_param_dict(self):
#         tuple_list = dict(self.get_param_values())
#         tuple_list.pop('name')
#         return tuple_list
#
#     def set_fix_value(self, obj, val):
#         """
#         Set a new value and make it non-modifiable
#         (e.g., for parameters read from the setup)
#         """
#         setattr(self, obj, val)
#         setattr(self.params(obj), 'constant', True)
#
#     def show_metadata_gui(self):
#         self.gui = self.get_gui(self)
#         self.gui.show()
#
#     def get_gui(self, save_button=True):
#         return ParameterGui(metadata_obj=self, save_button=save_button)
#
#
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
    framerate = param.Number(default=100, bounds=[0.5, 1000], doc='Frame rate (Hz)')
    gain = param.Number(default=1.0, bounds=[0.1, 3], doc='Camera amplification gain')

#
# class MetadataGeneral(Metadata):
#     """General experiment properties metadata class
#     """
#     category = 'general'
#
#     experiment_name = param.String()
#     experimenter_name = param.ObjectSelector(default='Vilim Stih',
#                                              objects=['Elena Dragomir',
#                                                       'Andreas Kist',
#                                                       'Laura Knogler',
#                                                       'Daniil Markov',
#                                                       'Pablo Oteiza',
#                                                       'Virginia Palieri',
#                                                       'Luigi Petrucco',
#                                                       'Ruben Portugues',
#                                                       'Vilim Stih',
#                                                       'Tugce Yildizoglu'
#                                                       ])
#
#     setup_name = param.ObjectSelector(default='Saskin', objects=['2p',
#                                                'Lightsheet',
#                                                '42',
#                                                'Saskin',
#                                                'Archimedes',
#                                                'Helmut',
#                                                'Katysha'])

