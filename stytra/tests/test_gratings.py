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


# iterate through the modules in the current package
package_dir = Path(st.__file__).parent / "examples"

protocols = []

for (_, module_name, _) in iter_modules([package_dir]):

    if module_name in ['gratings_exp']:
        
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

# gratings_exp -> pass
# eye_tracking_exp
# imaging_exp


@pytest.mark.parametrize("protocol", protocols)
def test_simple(qtbot, protocol):
    me = os.getpid()
    print(protocol, me)

    app = QApplication([])
    stytra_obj = st.Stytra(protocol=protocol(),
                        app=app,
                        exec=False)
    exp = stytra_obj.exp
    duration = exp.protocol_runner.duration
    print(duration)
    exp_wnd = exp.window_main
    tic = time()
    
    print("here t = 0")
    qtbot.wait(5000)
    print("here t = {}".format(time()-tic))
    qtbot.mouseClick(exp_wnd.toolbar_control.toggleStatus,
                    Qt.LeftButton,
                    delay=1)
    print("here t = {}".format(time()-tic))
    print("duration = {} min ".format(round(((duration + 1)*5)/60, 3)))


    try:
        qtbot.wait((duration + 1)*5000)
        print("1 try pass")
    except:
        print("Couldn't wait - error with qbot?")
    

    # qtbot.wait(10000)
    print("last here t = {}".format(time()-tic))
    # exp.end_protocol(save=False)
    try:
        print("2 try pass")
        exp_wnd.closeEvent(None)
    except:
        print("Couldn't close Event")
    qtbot.wait(5000)
    
    print("END -----------------------------------------------------------")
    # sleep(10)
    # print("try kill stuff")
    # os.kill(me, 9)
    # stytra_obj = 0
    # app = 0 
    # exp_wnd = 0
    # exp = 0
    


