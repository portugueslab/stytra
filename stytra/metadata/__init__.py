from stytra.utilities import HasPyQtGraphParams
from pyqtgraph.parametertree import Parameter, ParameterTree


class GuiMetadata(HasPyQtGraphParams):
    """General class for a group of metadata that can be controlled via
    a GUI.

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(self):
        super().__init__()
        self.protocol_params_tree = ParameterTree(showHeader=False)

    def get_param_dict(self):
        """ Return values of the parameters.

        Returns
        -------
            OrderedDict with the params values

        """
        return self.params.getValues()

    def show_metadata_gui(self):
        """ Create and return a ParameterTree window (documented
        `here <http://www.pyqtgraph.org/documentation/parametertree/index.html/>`_
        )

        Returns
        -------
            ParameterTree object to control the metadata

        """
        self.protocol_params_tree = ParameterTree(showHeader=False)
        self.protocol_params_tree.setParameters(self.params)
        self.protocol_params_tree.setWindowTitle("Metadata")
        self.protocol_params_tree.resize(450, 600)  # TODO figure out this window
        return self.protocol_params_tree


class GeneralMetadata(GuiMetadata):
    """General metadata for the experiment.
    """

    def __init__(self):
        super().__init__()
        self.params.setName("general_metadata")
        self.add_params(
            session_id=dict(type="int", value=0),
            experimenter_name=dict(type="list", value="", values=[""]),
            setup_name=dict(type="list", value="", values=[""]),
        )


class AnimalMetadata(GuiMetadata):
    """Metadata about the animal.
     """

    def __init__(self):
        super().__init__()
        self.params.setName("animal_metadata")
        self.add_params(
            id=dict(type="int", value=0),
            age=dict(
                type="int", value=7, limits=(3, 21), tip="Animal age", suffix="dpf"
            ),
            comments=dict(type="str", value=""),
            genotype=dict(type="list", values=[""], value=""),
        )
