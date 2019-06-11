import numpy as np
import pandas as pd
import unittest
import shutil
import tempfile
import glob
import json
import deepdish as dd

from stytra.experiments.tracking_experiments import TrackingExperiment
from PyQt5.QtWidgets import QApplication
from stytra.stimulation import Protocol, Pause

from lightparam import Param
from pathlib import Path

from time import sleep



class TestProtocol(Protocol):
    name = "test_protocol"

    def __init__(self):
        super().__init__()
        self.duration = Param(2)

    def get_stim_sequence(self):
        stimuli = [Pause(duration=self.duration)]
        return stimuli

class TestTrackingClass(unittest.TestCase):
    """
    Note: this test assumes that the default parameters for the tracking
    functions are the correct ones to track the videos in the examples/assets
    folder, from which the correct results are taken.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QApplication([])

        # True value computed from asset movies with default parameters:
        self.solutions = dict(
            th_e0=np.array([-95.58, -95.58, -95.58, -95.58, -95.58, -95.58, -95.58,
                  -95.58, -95.58, -95.58, -95.58, -95.58, -95.58, -95.58,
                  -95.58, -95.58, -95.58, -95.58, -95.58, -95.58]),
            th_e1=np.array([-77.34, -77.34, -77.34, -77.34, -77.34, -77.34, -79.74,
                  -79.74, -79.74, -79.74, -79.74, -79.56, -79.74, -79.74,
                  -79.74, -77.51, -77.51, -77.51, -77.51, -77.5]))

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def run_experiment(self, format, method):
        exp = TrackingExperiment(
            app=self.app,
            protocol=TestProtocol(),
            dir_save=self.test_dir,
            tracking=dict(method=method),
            camera=dict(
                video_file=str(Path(__file__).parent.parent / "examples" /
                               "assets" / "fish_compressed.h5")
            ),
            log_format=format
        )
        exp.start_experiment()
        exp.start_protocol()
        sleep(0.5)
        exp.acc_tracking.update_list()
        exp.end_protocol(save=True)
        exp.wrap_up()

    def check_result(self, array, key, tol=3):
        sol = self.solutions[key]
        assert ((sol - tol < array[:len(sol)]) &
                       (array[:len(sol)] < sol + tol)).all()


    def test_tracking(self):
        self.run_experiment("hdf5", "eyes")

        for path in Path(self.test_dir).glob("*/*/*.json"):
            with open(path, "r") as f:
                data = json.load(f)
            behavior_log = dd.io.load(path.parent / data[
                "tracking"][
                "behavior_log"], "/data")

            for k in ["th_e0", "th_e1"]:
                self.check_result(behavior_log[k].values, k)

        assert "test_protocol" in data["stimulus"]["protocol"].keys()
