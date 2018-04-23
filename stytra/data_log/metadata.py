from stytra.data_log import HasPyQtGraphParams
from pyqtgraph.parametertree import Parameter, ParameterTree


class GuiMetadata(HasPyQtGraphParams):
    """ General class for a group of metadata that have to be controlled via
    a GUI.
    """
    def __init__(self):
        super().__init__()
        self.protocol_params_tree = ParameterTree(showHeader=False)

    def get_param_dict(self):
        return self.params.getValues()

    def show_metadata_gui(self):
        self.protocol_params_tree = ParameterTree(showHeader=False)
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
                            'Tugce Yildizoglu',
                            'Ot Prat'],
                 },
                {'name': 'setup_name',  'type': 'list',
                 'values': ['test',
                            '2p',
                            'Lightsheet',
                            '42',
                            'Saskin',
                            'Archimedes',
                            'Helmut',
                            'Katyusha',
                            'WeltAmDraht'], 'value': 'test'}]

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
                            'GR90:Gal4;UAS:GCaMP6s',
                            '152:Gal4;UAS:GCaMP6s',
                            '156:Gal4;UAS:GCaMP6s',
                            'IO:Gal4;UAS:GCaMP6sef05'], 'value': 'TL'},
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
