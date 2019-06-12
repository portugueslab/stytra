import unittest
import shutil
import tempfile
import glob
import json
import numpy as np
import deepdish as dd

from stytra.experiments import VisualExperiment
from stytra.experiments.tracking_experiments import TrackingExperiment
from PyQt5.QtWidgets import QApplication
from stytra.stimulation import Protocol, Pause
from stytra.stimulation.stimuli import FullFieldVisualStimulus

from lightparam import Param
from pathlib import Path

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def clear_dir(self):
        for p in Path(self.test_dir).glob("*"):
            if p.is_dir():
                shutil.rmtree(p)

    @property
    def metadata_path(self):
        return next(Path(self.test_dir).glob("*/*/*.json"))

    def run_experiment(self, **kwargs):
        print(kwargs)
        # Weirdly, getattr(kwargs, "tracking", None) always returns None
        try:
            tracking = kwargs["tracking"]
        except KeyError:
            tracking = None

        if tracking is None:
            exp = VisualExperiment(
                app=self.app, dir_save=self.test_dir, **kwargs)
        else:
            exp = TrackingExperiment(app=self.app, dir_save=self.test_dir,
                **kwargs)

        exp.start_experiment()
        exp.start_protocol()
        sleep(0.5)
        if tracking is not None:
            exp.acc_tracking.update_list()
        exp.end_protocol(save=True)
        exp.wrap_up()

    @staticmethod
    def check_result(array, key, tol=3):
        solutions = dict(
            th_e0=np.array(
                [-95.58, -95.58, -95.58, -95.58, -95.58, -95.58, -95.58,
                 -95.58, -95.58, -95.58, -95.58, -95.58, -95.58, -95.58,
                 -95.58, -95.58, -95.58, -95.58, -95.58, -95.58]),
            th_e1=np.array(
                [-77.34, -77.34, -77.34, -77.34, -77.34, -77.34, -79.74,
                 -79.74, -79.74, -79.74, -79.74, -79.56, -79.74, -79.74,
                 -79.74, -77.51, -77.51, -77.51, -77.51, -77.5]),
            theta_00=np.array([-1.52, -1.52, -1.52, -1.52, -1.52, -1.52, -1.52,
                               -1.52, -1.52, -1.52, -1.52, -1.52, -1.52, -1.52,
                               -1.52, -1.52, -1.52, -1.52, -1.52, -1.52]),
            theta_08=np.array([-1.52, -1.52, -1.52, -1.52, -1.52, -1.52, -1.52,
                               -1.52, -1.52, -1.52, -1.52, -1.52, -1.52, -1.52,
                               -1.52, -1.52, -1.52, -1.52, -1.52, -1.52])
        )

        sol = solutions[key]
        assert ((sol - tol < array[:len(sol)]) &
                           (array[:len(sol)] < sol + tol)).all()

    def test_visual_experiment(self):
        self.app = QApplication([])
        for prot in [TestProtocol0(), TestProtocol1()]:
            self.run_experiment(protocol=prot)
            with open(self.metadata_path, "r") as f:
                    data = json.load(f)
            assert prot.name.split("/")[-1] in data["stimulus"][
                "protocol"].keys()

            self.clear_dir()

        trigger = DummyTrigger()
        self.run_experiment(protocol=TestProtocol(), scope_triggering=trigger)

        with open(self.metadata_path, "r") as f:
            data = json.load(f)
        assert "test_protocol" in data["stimulus"]["protocol"].keys()
        self.clear_dir()

    def test_tracking_experiments(self):
        """ Note: this test assumes that the default parameters for the tracking
        functions are the correct ones to track the videos in the examples/assets
        folder, from which the correct results have been calculated.
        """
        self.app = QApplication([])

        video_file = str(Path(__file__).parent.parent / "examples" /
                           "assets" / "fish_compressed.h5")

        for method in ["eyes", "tail"]:
            self.run_experiment(protocol=TestProtocol(),
                                camera=dict(video_file=video_file),
                                tracking=dict(method=method),
                                log_format="hdf5")
            with open(self.metadata_path, "r") as f:
                data = json.load(f)

            behavior_log = dd.io.load(self.metadata_path.parent / data[
                "tracking"]["behavior_log"], "/data")

            assert method == data["general"]["program_version"]["arguments"]["tracking"]["method"]

            if method == "tail":
                for k in ["theta_00", "theta_08"]:
                    self.check_result(behavior_log[k].values, k)
            elif method == "eyes":
                for k in ["th_e0", "th_e1"]:
                    self.check_result(behavior_log[k].values, k)

            self.clear_dir()
