import argparse
from stytra.experiments import Experiment
from stytra.experiments.tracking_experiments import (
    CameraExperiment,
    TrackingExperiment,
    SwimmingRecordingExperiment,
)

# imports for easy experiment building
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation import Protocol

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon


class Stytra:
    """ Stytra application instance. Contains the QApplication and
    constructs the appropriate experiment object for the specified
    parameters"""

    def __init__(
        self,
        protocols=[],
        metadata_animal=None,
        metadata_general=None,
        camera_config=None,
        display_config=None,
        tracking_config=None,
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
        )

        base = Experiment

        if camera_config is not None:
            base = CameraExperiment
            class_kwargs["camera_config"] = camera_config
            if tracking_config is not None:
                class_kwargs["tracking_config"] = tracking_config
                if tracking_config["embedded"]:
                    base = TrackingExperiment
                else:
                    base = SwimmingRecordingExperiment
                # TODO add swimming closed-loop experiments

        app_icon = QIcon()
        app_icon.addFile("icons/48.png", QSize(48, 48))
        app_icon.addFile("icons/128.png", QSize(128, 128))
        app_icon.addFile("icons/256.png", QSize(256, 256))
        app.setWindowIcon(app_icon)

        exp = base(**class_kwargs)

        exp.start_experiment()

        app.exec_()


if __name__ == "__main__":
    st = Stytra()
