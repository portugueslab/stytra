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
            full_screen : bool
            window_size : tuple(int, int)
                optional specification of the size of the stimulus display area

        camera_config : dict
            file
                or
            type: str
                "ximea" or "avt" cameras are currently supported

            rotation: int
                how many times to rotate the camera image by 90 degrees to get the
                right orientation, matching the projcetor

            downsampling: int
                how many times to downsample the image (for ximea cameras)


        tracking_config : dict
            preprocessing_method: str
                one of "prefilter" or "bgrem"
            tracking_method: str
                one of "tail", "eyes", "fish"
            estimator: str
                for closed-loop experiments: either "vigor" or "lstm" for embedded experiments
                    or "fish" for freely-swimming ones

        recording_config : bool
            for video-recording experiments

        embedded : bool
            if not embedded, use circle calibrator to match the camera and projector

        dir_assets : str
            the location of assets used for stimulation (pictures, videos, models
            for closed loop etc.)

        dir_save : str
            directory where the experiment data will be saved

        metadata_animal : class
            subclass of AnimalMetadata adding information from a specific lab
            (species, genetic lines, pharmacological treatments etc.)

        metdata_general : class
            subclass of GeneralMetadata, containing lab-specific information
            (setup names, experimenter names...)

        record_stim_every: int
            if non-0 recodrds the displayed stimuli into an array which is
            saved alongside the other data.

        trigger : object
            a trigger object, synchronising stimulus presentation
            to imaging acquisition

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
        dir_assets=None,
        dir_save=None,
        record_stim_every=None,
    ):

        app = QApplication([])

        class_kwargs = dict(
            app=app,
            dir_save=dir_save,
            asset_directory=dir_assets,
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
