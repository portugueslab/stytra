import unittest
import shutil
import tempfile
import glob
import json

from stytra.experiments import VisualExperiment
from PyQt5.QtWidgets import QApplication
from stytra.stimulation import Protocol, Pause
from stytra.stimulation.stimuli import FullFieldVisualStimulus

from lightparam import Param

from stytra.triggering import Trigger
from time import sleep

import pytest

class TestProtocol0(Protocol):
    name = "test_protocol_0"

    def __init__(self):
        super().__init__()
        self.duration = Param(0.01)

    def get_stim_sequence(self):
        stimuli = [Pause(duration=self.duration)]
        return stimuli


class TestProtocol1(Protocol):
    name = "test_protocol_1"

    def __init__(self):
        super().__init__()
        self.duration = Param(0.01)

    def get_stim_sequence(self):
        stimuli = [FullFieldVisualStimulus(duration=self.duration)]
        return stimuli


class DummyTrigger(Trigger):
    def __init__(self):
        super().__init__()
        self.k = False

    def check_trigger(self):
        if self.k:
            sleep(0.5)
            self.k = False
            return True
        else:
            self.k = True
            return False


class TestProtocol(Protocol):
    name = "test_protocol"

    def get_stim_sequence(self):
        return [Pause(duration=0.5)]


@pytest.mark.last
class TestExperimentClass(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app = QApplication([])

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_experiment_class(self):
        for prot in [TestProtocol0, TestProtocol1]:
            exp = VisualExperiment(
                app=self.app, protocol=prot(), dir_save=self.test_dir
            )
            exp.start_experiment()
            exp.start_protocol()
            exp.end_protocol(save=True)
            exp.wrap_up()

        data = []
        for path in sorted(glob.glob(self.test_dir + "/*/*/*.json")):
            with open(path, "r") as f:
                data.append(json.load(f))

        assert "test_protocol_0" in data[0]["stimulus"]["protocol"].keys()
        assert "test_protocol_1" in data[1]["stimulus"]["protocol"].keys()

    def test_trigger(self):
        trigger = DummyTrigger()
        exp = VisualExperiment(
            app=self.app,
            protocol=TestProtocol(),
            dir_save=self.test_dir,
            scope_triggering=trigger,
        )
        exp.start_experiment()
        exp.start_protocol()
        exp.end_protocol(save=True)
        exp.wrap_up()

        for path in sorted(glob.glob(self.test_dir + "/*/*/*.json")):
            with open(path, "r") as f:
                data = json.load(f)

        assert "test_protocol" in data["stimulus"]["protocol"].keys()
