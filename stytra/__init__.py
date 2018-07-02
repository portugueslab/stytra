import argparse
from stytra.experiments import Experiment
from stytra.experiments.tracking_experiments import (
    CameraExperiment,
    TrackingExperiment,
    SwimmingRecordingExperiment,
)
from stytra.calibration import CircleCalibrator

# imports for easy experiment building
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation import Protocol

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

import pkg_resources

class Stytra:
    """ Stytra application instance. Contains the QApplication and
    constructs the appropriate experiment object for the specified
    parameters

    Parameters
    ==========
        protocols : list(Protocol)
            the protocols to be made available from the dropdown

        display_config : dict
            full_screen
            window_size

        camera_config : dict
            file
                or
            type
            rotation
            downsampling


        tracking_config : dict
            preprocessing_method: str
                one of "prefilter" or "bgrem"
            tracking_method: str
                one of "tail", "eyes", "fish"
            estimator: str


        recording_config : bool
            whether to record motion in freely-swimming experiments

        embedded : bool
            if not embedded, use circle calibrator



    """

    def __init__(
        self,
        protocols=[],
        metadata_animal=None,
        metadata_general=None,
        camera_config=None,
        display_config=None,
        tracking_config=None,
        recording_config=None,
            embedded=True,
        trigger=None,
        asset_dir=None,
        dir_save=None,
        record_stim_every=None,
    ):

        app = QApplication([])

        class_kwargs = dict(
            app=app,
            dir_save=dir_save,
            asset_directory=asset_dir,
            rec_stim_every=record_stim_every,
            metadata_animal=metadata_animal,
            metadata_general=metadata_general,
            display_config=display_config,
            protocols=protocols,
            trigger=trigger,
            calibrator=(CircleCalibrator() if not embedded else None),
        )

        base = Experiment

        if camera_config is not None:
            base = CameraExperiment
            class_kwargs["camera_config"] = camera_config
            if tracking_config is not None:
                class_kwargs["tracking_config"] = tracking_config
                base = TrackingExperiment
            if recording_config is not None:
                base = SwimmingRecordingExperiment

        app_icon = QIcon()
        for size in [32, 64, 128, 256]:
            app_icon.addFile(pkg_resources.resource_filename(__name__, "/icons/{}.png".format(size)),
                             QSize(size, size))
        app.setWindowIcon(app_icon)

        exp = base(**class_kwargs)

        exp.start_experiment()

        app.exec_()


if __name__ == "__main__":
    st = Stytra()
