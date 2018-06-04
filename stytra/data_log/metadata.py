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
        self.protocol_params_tree.resize(450,
                                         600)  # TODO figure out this window
        return self.protocol_params_tree

    def get_state(self):
        return self._params.saveState()

    def restore_state(self):
        pass


class GeneralMetadata(GuiMetadata):
    def __init__(self):
        super().__init__()
        self.params.setName('general_metadata')
        self.add_params(session_id=dict(type='int', value=0),
                        experimenter_name=dict(type='list', value='',
                                               values=['']),
                        setup_name=dict(type='list', value='',
                                        values=['']))


class FishMetadata(GuiMetadata):
    def __init__(self):
        super().__init__()
        self.add_params(id=dict(type='int', value=0),
                        age=dict(type='int', value=7, limits=(3, 21),
                                 tip='Fish age', suffix='dpf'),
                        genotype=dict(type='list',
                                      values=[''],
                                      value=''),
                        dish_diameter=dict(type='list', value='',
                                           values=['',
                                                   '30',
                                                   '60',
                                                   '90',
                                                   'lightsheet']),
                        comments=dict(type='str', value=''),
                        embedded=dict(type='bool', value=True),
                        treatment=dict(type='list', value='',
                                       values=['']),
                        screened=dict(type='list', value='not',
                                      values=['not',
                                              'dark',
                                              'bright']))

        self.params.setName('fish_metadata')
