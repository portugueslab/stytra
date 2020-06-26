from time import sleep

from lightparam import Param
import stytra

from stytra.stimulation import Protocol, Pause
from stytra.experiments import VisualExperiment
from stytra.stimulation.stimuli import FullFieldVisualStimulus
from stytra.triggering import Trigger
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


PROTOCOL_DURATION = 4  # Duration of each simulated experiment
N_REFRESH_EVTS = 50

import pytest


class TestProtocol0(Protocol):
    name = "test_protocol"

    def __init__(self):
        super().__init__()
        self.duration = Param(PROTOCOL_DURATION / 2)

    def get_stim_sequence(self):
        stimuli = [Pause(duration=self.duration),
                   FullFieldVisualStimulus(duration=self.duration)]
        return stimuli


class DummyTrigger(Trigger):
    def __init__(self):
        super().__init__()
        self.k = False

    def check_trigger(self):
        if self.k:
            sleep(PROTOCOL_DURATION / 5)
            self.k = False
            return True
        else:
            self.k = True
            return False


def test_exp(experiment_factory, temp_dir, qtbot):
    exp, exp_wnd = experiment_factory(VisualExperiment,
                             protocol=TestProtocol0(),
                             dir_save=temp_dir
                             )
    qtbot.addWidget(exp_wnd)
    qtbot.mouseClick(exp_wnd.toolbar_control.toggleStatus,
                     Qt.LeftButton,
                     delay=1)
    qtbot.wait((PROTOCOL_DURATION + 1)*1000)
    #qtbot.mousePress(exp_wnd)
    #for _ in range(N_REFRESH_EVTS):
     #   exp.protocol_runner.timestep()
     #   sleep(PROTOCOL_DURATION / N_REFRESH_EVTS)
    #if tracking is not None:
    #    exp.acc_tracking.update_list()
    exp.end_protocol(save=True)

from PyQt5.QtWidgets import QWidget

# def test_wind(widg_factory):
#     a = widg_factory()
#     a.show()
