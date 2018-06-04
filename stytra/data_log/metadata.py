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
        params =[dict(name='session_id', type='int', value=0),
                 dict(name='experimenter_name', type='list', value='',
                      values=['']),
                 dict(name='setup_name', type='list', value='',
                      values=[''])]

        self.params.setName('general_metadata')
        self.params.addChildren(params)


class FishMetadata(GuiMetadata):
    def __init__(self):
        super().__init__()
        params = [dict(name='id', type='int', value=0),
                  dict(name='age', type='int', value=7, limits=(3, 21),
                       tip='Fish age', suffix='dpf'),
                  dict(name='genotype', type='list',
                       values=[''],
                       value=''),
                  dict(name='dish_diameter', type='list', value='',
                       values=['',
                               '30',
                               '60',
                               '90',
                               'lightsheet']),
                  dict(name='comments', type='str', value=''),
                  dict(name='embedded', type='bool', value=True),
                  dict(name='treatment', type='list', value='',
                       values=['']),
                  dict(name='screened', type='list', value='not',
                       values=['not',
                               'dark',
                               'bright'])]
        self.params.setName('fish_metadata')
        self.params.addChildren(params)
