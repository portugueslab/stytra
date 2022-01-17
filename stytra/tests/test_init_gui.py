from time import sleep, time

from lightparam import Param
import stytra

from stytra.stimulation import Protocol, Pause
from stytra.experiments import VisualExperiment
from stytra.stimulation.stimuli import FullFieldVisualStimulus
from stytra.triggering import Trigger
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import stytra as st
from pathlib import Path
from pkgutil import iter_modules
from importlib import import_module
import pytest

# iterate through the modules in the current package
package_dir = Path(st.__file__).parent / "examples"

protocols = []
for (_, module_name, _) in iter_modules([package_dir]):

    # import the module and iterate through its attributes
    try:
        module = import_module(f"stytra.examples.{module_name}")
    except ImportError as e:
        print(
            "Error during import of: {}\nSee full message here:\n{}".format(
                module_name, e
            )
        )
    except ModuleNotFoundError as e:
        print(
            "module '{}' not found.\nSee full message here:\n{}".format(module_name, e)
        )

    # check if external harware is required to run the example
    if (
        "REQUIRES_EXTERNAL_HARDWARE" in dir(module)
        and getattr(module, "REQUIRES_EXTERNAL_HARDWARE") == True
    ):
        pass
    else:
        for attribute_name in dir(module):
            if "Protocol" in attribute_name and attribute_name != "Protocol":
                protocols.append(getattr(module, attribute_name))


# only tests initialization
@pytest.mark.parametrize("protocol", protocols)
def test_base_exp(qtbot, protocol):

    print("Testing gui Protocol: ", protocol)
    tic = time()
    print("Start: t = 0")

    # Initialize app
    app = QApplication([])
    stytra_obj = st.Stytra(protocol=protocol(), app=app, exec=False)
    exp = stytra_obj.exp
    duration = exp.protocol_runner.duration
    exp_wnd = exp.window_main

    # Close app
    qtbot.wait(5000)
    print("Finished: t = {:.1f}".format(time() - tic))

    exp_wnd.closeEvent(None)
    qtbot.wait(5000)
    print("END: t = {:.1f}".format(time() - tic))
