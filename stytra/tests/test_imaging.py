from time import sleep,time

from lightparam import Param
import stytra
import os
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
import psutil
import threading


# iterate through the modules in the current package
package_dir = Path(st.__file__).parent / "examples"

protocols = []

for (_, module_name, _) in iter_modules([package_dir]):

    if module_name in ['imaging_exp']:
        
#         # import the module and iterate through its attributes
            try:
                module = import_module(f"stytra.examples.{module_name}")
            except ImportError as e:
                print("Error in: {}\nSee full message here:\n{}".format(module_name,e))
            
            for attribute_name in dir(module):
                if "Protocol" in attribute_name and attribute_name != "Protocol":
                    protocols.append(getattr(module, attribute_name))
            # attribute = getattr(module, attribute_name)
        # except ModuleNotFoundError:
        #    print(f"Can't import {module}")


# ! Never ending process, stucks the command line -> only testing gui initialization
@pytest.mark.parametrize("protocol", protocols)
def test_simple(qtbot, protocol):

    print("Testing gui Protocol: ",protocol)
    tic = time()
    print("Start: t = 0")

    # Initialize app
    app = QApplication([])
    stytra_obj = st.Stytra(protocol=protocol(),
                        app=app,
                        exec=False)
    exp = stytra_obj.exp
    duration = exp.protocol_runner.duration
    exp_wnd = exp.window_main


    qtbot.wait(5000)
    print("Checkpoint 1: t = {}".format(time()-tic))
    # qtbot.mouseClick(exp_wnd.toolbar_control.toggleStatus,
    #                 Qt.LeftButton,
    #                 delay=1)

    try:
        d = (duration + 1)*5000
        if d> 400000:
            d = 40000
        print("Duration = {} min".format(int(d/60)))
        qtbot.wait(d)
        sleep(5)
    except:
        print("Couldn't wait - error with qbot?")
    


    print("Finished: t = {}".format(time()-tic))

    # Close app
    try:
        exp_wnd.closeEvent(None)
    except:
        print("Couldn't close Event")
    qtbot.wait(5000)


    print("END: t = {}".format(time()-tic))




