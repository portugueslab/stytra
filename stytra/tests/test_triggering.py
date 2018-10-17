import unittest
import shutil
import tempfile
import numpy as np
import glob
import deepdish as dd
import json
from pathlib import Path
from time import sleep

from stytra.experiments import Experiment
from PyQt5.QtWidgets import QApplication
from stytra.stimulation import Protocol, Pause
from stytra.triggering import Trigger


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


class TestExperimentClass(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_experiment_class(self):
        class TestProtocol(Protocol):
            name = "test_protocol"

            def get_stim_sequence(self):
                return [Pause(duration=0.5)]

        trigger = DummyTrigger()
        app = QApplication([])
        exp = Experiment(
            app=app,
            protocols=[TestProtocol],
            dir_save=self.test_dir,
            scope_triggering=trigger,
        )
        exp.start_experiment()

        exp.start_protocol()
        exp.end_protocol(save=True)
        exp.wrap_up()

        data = []
        for path in sorted(glob.glob(self.test_dir + "/*/*.json")):
            with open(path, "r") as f:
                data.append(json.load(f))

        np.testing.assert_equal(
            data[0]["stimulus"]["protocol_params"]["name"], "test_protocol"
        )
