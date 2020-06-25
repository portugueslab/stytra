from time import sleep

from lightparam import Param
import stytra

from stytra.stimulation import Protocol, Pause
from stytra.experiments import VisualExperiment
from stytra.stimulation.stimuli import FullFieldVisualStimulus
from stytra.triggering import Trigger
from PyQt5.QtWidgets import QApplication

PROTOCOL_DURATION = 5  # Duration of each simulated experiment
N_REFRESH_EVTS = 5

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


def test_exp(experiment_factory, temp_dir):
    exp, _ = experiment_factory(VisualExperiment,
                             protocol=TestProtocol0(),
                             dir_save=temp_dir
                             )
    exp.start_protocol()
    for _ in range(N_REFRESH_EVTS):
        exp.protocol_runner.timestep()
        sleep(PROTOCOL_DURATION / N_REFRESH_EVTS)
    #if tracking is not None:
    #    exp.acc_tracking.update_list()
    exp.end_protocol(save=True)
    assert True