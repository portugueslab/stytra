import unittest
import shutil
import tempfile
import numpy as np
import glob
import deepdish as dd
import json

from stytra.experiments import VisualExperiment
from PyQt5.QtWidgets import QApplication
from stytra.stimulation import Protocol, Pause
from stytra.stimulation.stimuli import FullFieldVisualStimulus


class TestExperimentClass(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_experiment_class(self):
        class TestProtocol0(Protocol):
            name = "test_protocol_0"

            def __init__(self):
                super().__init__()
                self.add_params(duration=0.01)

            def get_stim_sequence(self):
                stimuli = [Pause(duration=self.params["duration"])]
                return stimuli

        class TestProtocol1(Protocol):
            name = "test_protocol_1"

            def __init__(self):
                super().__init__()
                self.add_params(duration=0.01)

            def get_stim_sequence(self):
                stimuli = [
                    FullFieldVisualStimulus(
                        duration=self.params["duration"], color=(255,) * 3
                    )
                ]
                return stimuli

        app = QApplication([])
        exp = VisualExperiment(
            app=app, protocols=[TestProtocol0, TestProtocol1], dir_save=self.test_dir
        )
        exp.start_experiment()

        exp.metadata_animal.show_metadata_gui()
        exp.metadata.show_metadata_gui()
        exp.window_main.widget_control.combo_prot.setCurrentText("test_protocol_0")
        exp.start_protocol()
        exp.end_protocol(save=True)

        exp.window_main.widget_control.combo_prot.setCurrentText("test_protocol_1")
        exp.start_protocol()
        exp.end_protocol(save=True)

        exp.wrap_up()

        data = []
        for path in sorted(glob.glob(self.test_dir + "/*/*.json")):
            with open(path, "r") as f:
                data.append(json.load(f))

        np.testing.assert_equal(
            data[0]["stimulus"]["protocol_params"]["name"], "test_protocol_0"
        )

        np.testing.assert_equal(
            data[1]["stimulus"]["protocol_params"]["name"], "test_protocol_1"
        )
