import tempfile
from pathlib import Path
from shutil import rmtree
import pytest
from PyQt5.QtWidgets import QApplication
import warnings
from typing import List
from stytra.experiments import Experiment


@pytest.fixture()
def temp_dir():
    new_dir = Path(tempfile.mkdtemp())
    yield new_dir
    rmtree(new_dir)


@pytest.fixture(scope="function")
def app(qtbot):
    """A modified qtbot fixture that makes sure no widgets have been leaked.
    Code from  Napari tests.
    """
    app = QApplication([])
    initial = QApplication.topLevelWidgets()
    yield app
    QApplication.processEvents()
    leaks = set(QApplication.topLevelWidgets()).difference(initial)
    # still not sure how to clean up some of the remaining vispy
    if any([n.__class__.__name__ != 'CanvasBackendDesktop' for n in leaks]):
        raise AssertionError(f'Widgets leaked!: {leaks}')
    if leaks:
        warnings.warn(f'Widgets leaked!: {leaks}')


@pytest.fixture(scope="function")
def experiment_factory(app):
    experiments: List[Experiment] = []

    def actual_factory(ExpClass, *args, **kwargs):
        # app = QApplication([])
        exp = ExpClass(*args, **kwargs, app=app)
        exp.start_experiment()

        return exp, exp.window_main

    yield actual_factory

    for exp in experiments:
        exp.wrap_up()
