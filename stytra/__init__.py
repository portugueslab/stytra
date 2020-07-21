__author__ = """Vilim Stih & Luigi Petrucco @portugueslab"""
__version__ = "0.8.34"


from stytra.core import Stytra
from stytra.stimulation import Protocol
from stytra.metadata import AnimalMetadata, GeneralMetadata
import multiprocessing

# Required for multiprocessing to behave properly on macOS:
multiprocessing.set_start_method('spawn', force=True)
