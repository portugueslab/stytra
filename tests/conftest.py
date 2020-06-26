import tempfile
from pathlib import Path
from shutil import rmtree
import pytest
from PyQt5.QtWidgets import QApplication, QWidget
import warnings
from typing import List
from stytra.experiments import Experiment


@pytest.fixture()
def temp_dir():
    new_dir = Path(tempfile.mkdtemp())
    yield new_dir
    rmtree(new_dir)


# @pytest.fixture(scope="function")
# def qtbot(qtbot):
#     """A modified qtbot fixture that makes sure no widgets have been leaked.
#     Code from  Napari tests.
#     """
#
#     initial = QApplication.topLevelWidgets()
#     print(initial)
#     yield qtbot
#     print("Checking")
#     QApplication.processEvents()
#     leaks = set(QApplication.topLevelWidgets()).difference(initial)
#     # still not sure how to clean up some of the remaining vispy
#     if any([n.__class__.__name__ != 'CanvasBackendDesktop' for n in leaks]):
#         raise AssertionError(f'Widgets leaked!: {leaks}')
#     if leaks:
#         warnings.warn(f'Widgets leaked!: {leaks}')


@pytest.fixture(scope="function")
def experiment_factory(qtbot):
    experiments = []

    def actual_factory(ExpClass, *args, **kwargs):
        exp = ExpClass(*args, **kwargs)
        exp.start_experiment()
        experiments.append(exp.window_main)
        QApplication.processEvents()
        return exp, exp.window_main


    yield actual_factory
    for i, exp in enumerate(experiments):
        # exp.closeEvent()
        pass


# @pytest.fixture(scope="function")
# def widg_factory(qtbot):
#     # experiments = []
#
#     def actual_factory():
#         # app = QApplication([])
#         wid = QWidget()
#
#         return wid
#
#     yield actual_factory
#     # print("Closing")
#     # for i, exp in enumerate(experiments):
#     #     exp.closeEvent()
