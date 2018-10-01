from stytra.utilities import HasPyQtGraphParams
from pyqtgraph.parametertree import Parameter, ParameterTree
from poparam import Parametrized, Param

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


class GeneralMetadata(Parametrized):
    """General metadata for the experiment.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(name="general/basic", **kwargs)
        self.session_id = Param(0, limits=(0,100))
        self.experimenter_name = Param("", limits=[""])
        self.setup_name = Param("", limits=[""])


class AnimalMetadata(Parametrized):
    """Metadata about the animal.
     """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="general/animal", **kwargs)
        self.id = Param(0, limits=(0, 100))
        self.age = Param(7, limits=(3, 21), desc="age of the animal")
        self.comments = Param("", desc="Comments on the animal or experiment")
        self.genotype = Param("",[""])
