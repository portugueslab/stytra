import multiprocessing as mp

from stytra.experiments import VisualExperiment
from stytra.experiments.tracking_experiments import (
    CameraVisualExperiment,
    TrackingExperiment,
)
from stytra.experiments.camera_recording_experiment import VideoRecordingExperiment
from stytra.calibration import CircleCalibrator
from stytra.utilities import recursive_update

# imports for easy experiment building
from stytra.metadata import AnimalMetadata, GeneralMetadata
from stytra.stimulation import Protocol

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

import pkg_resources
import qdarkstyle
import pyqtgraph as pg
import json

from pathlib import Path

class Stytra:
    """ Stytra application instance. Contains the QApplication and
    constructs the appropriate experiment object for the specified
    parameters

    Parameters
    ==========
        protocol : Protocol
            the protocols to be made available from the dropdown

        display : dict
            full_screen : bool
                displays the stimulus full screen on the secondary monitor, otherwise
                it is in a window
            window_size : tuple(int, int)
                optional specification of the size of the stimulus display area

        camera : dict
            video_file : str
                or
            type: str
                supported cameras are
                "ximea" (with the official API)
                "avt" (With the Pymba API)
                "spinnaker" (PointGray/FLIR)
                "mikrotron" (via NI Vision C API)

            rotation: int
                how many times to rotate the camera image by 90 degrees to get the
                right orientation, matching the projector

            downsampling: int
                how many times to downsample the image (for some ximea cameras)

            roi: tuple of int (x, y, w, h)
                ROI for cameras that support it

            max_buffer_length: int, default 1000
                the maximal length of the replay buffer in frames, can to be adjusted
                depending on the memory of the computer and the camera resolution
                and framerate

        tracking : dict
            preprocessing_method: str, optional
               "prefilter" or "bgsub"
            method: str
                one of "tail", "eyes" or "fish"
            estimator: str or class
                for closed-loop experiments: either "vigor" for embedded experiments
                    or "position" for freely-swimming ones. A custom estimator can be supplied.

        recording : bool
            for video-recording experiments

        embedded : bool
            if not embedded, use circle calibrator
            to match the camera and projector

        dir_assets : str
            the location of assets used for stimulation (pictures, videos, models
            for closed loop etc.)

        dir_save : str
            directory where the experiment data will be saved

        metadata_animal : class
            subclass of AnimalMetadata adding information from a specific lab
            (species, genetic lines, pharmacological treatments etc.)

        metadata_general : class
            subclass of GeneralMetadata, containing lab-specific information
            (setup names, experimenter names...)

        record_stim_framerate: int
            if non-0 recodrds the displayed stimuli into an array which is
            saved alongside the other data.

        trigger : object
            a trigger object, synchronising stimulus presentation
            to imaging acquisition

        n_tracking_processes : int
            number of tracking processes to be used. Using more than 1 can improve performance
            but also cause issues in state-dependent tracking functions.

    """

    def __init__(self, recording=None, exec=True, app=None,
                 **kwargs):
        # Check if exist a default config file in the home (user) directory:
        mp.set_start_method("spawn", force=True)
        inum = kwargs.get("instance_number", -1)
        if inum >= 0:
            default_config_file = Path.home() / "stytra_setup_config_{}.json".format(inum)
        else:
            default_config_file = Path.home() / "stytra_setup_config.json"
        if default_config_file.is_file():
            config = json.load(open(str(default_config_file)))
        else:
            config = dict()

        # Get rest of configuration parameters from the protocol:
        try:
            extra_config = kwargs["protocol"].stytra_config
            recursive_update(config, extra_config)
        except AttributeError:
            pass

        recursive_update(config, kwargs)  # Use also keyword arguments

        if config.get("scope_triggering", None) == "zmq":
            # Automatically use zmqTrigger if zmq is specified
            from stytra.triggering import ZmqTrigger

            config["scope_triggering"] = ZmqTrigger(port="5555")

        if app is None:
            app = QApplication([])
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            if app.devicePixelRatio() > 1:
                app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        class_kwargs = dict(app=app)
        class_kwargs.update(config)

        base = VisualExperiment

        if "camera" in class_kwargs.keys():
            base = CameraVisualExperiment
            if "tracking" in class_kwargs.keys():
                base = TrackingExperiment
                if not class_kwargs["tracking"].get("embedded", True):
                    class_kwargs["calibrator"] = CircleCalibrator()

            if recording:
                base = VideoRecordingExperiment

        # Stytra logo
        app_icon = QIcon()
        for size in [32, 64, 128, 256]:
            app_icon.addFile(
                pkg_resources.resource_filename(__name__, "/icons/{}.png".format(size)),
                QSize(size, size),
            )
        app.setWindowIcon(app_icon)

        pg.setConfigOptions(imageAxisOrder="row-major")

        self.exp = base(**class_kwargs)

        self.exp.start_experiment()
        if exec:
            app.exec_()
