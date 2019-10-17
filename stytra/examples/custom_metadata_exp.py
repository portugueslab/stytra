from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.metadata import AnimalMetadata
from lightparam import Param

# Little example to showcase metadata customization and parameters
# Here, define new class of metadata required for your model animal of choice
class KrakenMetadata(AnimalMetadata):
    def __init__(self, **kwargs):
        # We will define all metadata as Parameters.
        super().__init__(**kwargs)

        # String parameter. Setting the loadable flag to false prevent this
        # parameter to be restored frin the stytra_last_config file, and the
        # editable to false to make it not changable in the interface:
        self.species = Param("Kraken kraken", loadable=False, editable=False)
        # String parameter with a default and a description.
        # The description appears hovering with mouse.
        self.location = Param(
            "North Atlantic", desc="Approximate location of the sightening"
        )
        # Drop down menu, for multiple choices:
        self.diet = Param("Humans", ["Humans", "Ships", "Unknown"])
        # Redefine age with units:
        self.age = Param(500, limits=(1, 10000), unit="years")
        # A simple integer, with limits:
        self.n_tentacles = Param(8, limits=(1, 200))
        # An integer with inferior boundary only (no upper limit for the terror):
        self.n_casualties = Param(8, limits=(1, None))
        # A simple float, with limits and measure units:
        self.dimensions = Param(8.0, limits=(0.5, 100), unit="m")

        # Some parameters are already defined in the AnimalMetadata class
        # (species, genotype, comments, id). Here we overwrite them:
        self.id = Param("")


# Define some uninteresting stytra protocol for our docile animal:
class FlashProtocol(Protocol):
    name = "empty_protocol"

    def get_stim_sequence(self):
        return [Pause(duration=4.0)]


# Finally, just pass Stytra the new class with the keyword "metadata_animal":
# Remember to pass the metadata class - KrakenMetadata - and not the object
# - KrakenMetadata().
# If you are testing Stytra functionalities you might want to remove the
# "stytra_last_config.json" file from user folder after testing this!
if __name__ == "__main__":
    st = Stytra(protocol=FlashProtocol(), metadata_animal=KrakenMetadata)
