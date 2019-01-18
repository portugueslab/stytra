from lightparam import Parametrized, Param


class GeneralMetadata(Parametrized):
    """General metadata for the experiment.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(name="general/basic", **kwargs)
        self.session_id = Param(0, limits=(0, 100))
        self.experimenter_name = Param("")
        self.setup_name = Param("")


class AnimalMetadata(Parametrized):
    """Metadata about the animal.
     """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="general/animal", **kwargs)
        self.id = Param(0, limits=(0, 100))
        self.age = Param(7, limits=(3, 21), desc="age of the animal")
        self.comments = Param("", desc="Comments on the animal or experiment")
        self.genotype = Param("")
