import unittest
import tempfile
import pkg_resources
import numpy as np
import pandas as pd
from stytra.stimulation.stimuli import (
    DynamicLuminanceStimulus,
    GratingStimulus,
    WindmillStimulus,
    SeamlessImageStimulus,
    InterpolatedStimulus,
    RadialSineStimulus,
)

from stytra.stimulation import Protocol

from time import sleep
from stytra import Stytra

import shutil
import stytra

from os import path
from pathlib import Path


class RadialSine(Protocol):
    """ Demonstrates usage of luminance stimuli

    """

    name = "radial_sine"

    def get_stim_sequence(self):
        return [RadialSineStimulus(duration=2, period=10, velocity=5)]


class FullFieldProtocol(Protocol):
    """ Demonstrates usage of luminance stimuli

    """

    name = "full_field"

    def get_stim_sequence(self):
        lum = pd.DataFrame(dict(t=[0, 1, 2], luminance=[0.0, 1.0, 0.0]))
        return [
            DynamicLuminanceStimulus(df_param=lum, clip_mask=(0.0, 0.0, 0.5, 0.5)),
            DynamicLuminanceStimulus(df_param=lum, clip_mask=(0.5, 0.5, 0.5, 0.5)),
        ]


class OKRProtocol(Protocol):
    """ Demonstrates usage of OKR evoking windmill stimuli

    """

    name = "okr"

    def get_stim_sequence(self):
        Stim = type(
            "stim", (InterpolatedStimulus, WindmillStimulus), {}  # order is important!
        )
        return [Stim(df_param=pd.DataFrame(dict(t=[0, 2, 4], theta=[0, np.pi / 8, 0])))]


class GratingProtocol(Protocol):
    name = "grating"

    def get_stim_sequence(self):
        Stim = type("stim", (InterpolatedStimulus, GratingStimulus), dict())
        return [
            Stim(df_param=pd.DataFrame(dict(t=[0, 2], vel_x=[10, 10], theta=np.pi / 4)))
        ]


class SeamlessImageProtocol(Protocol):
    name = "seamless_image"

    def get_stim_sequence(self):
        Stim = type("stim", (SeamlessImageStimulus, InterpolatedStimulus), {})
        return [
            Stim(
                background="caustics.png",
                df_param=pd.DataFrame(dict(t=[0, 2], vel_x=[10, 10], vel_y=[5, 5])),
            )
        ]


class GenerateStimuliMovie(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.stopped = False
        self.protocols = []
        self.protocol_name = ""
        self.exp = None

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def waitend(self):
        print("At the end")
        output_folder = (
            path.dirname(pkg_resources.resource_filename(stytra.__name__, ""))
            + "/docs/source/_static/"
        )
        shutil.copy(
            next(Path(self.exp.folder_name).glob("*stim_movie.mp4")),
            output_folder + "stim_movie_" + self.protocol_name + ".mp4",
        )
        sleep(0.5)
        self.exp.wrap_up()

    def test_stimulus_rendering(self):
        asset_dir = pkg_resources.resource_filename(__name__, "/test_assets")

        self.protocols = [
            GratingProtocol,
            RadialSine,
            FullFieldProtocol,
            OKRProtocol,
            SeamlessImageProtocol,
        ]

        for protocol in self.protocols[-1:]:
            self.protocol_name = protocol.name

            s = Stytra(
                protocol=protocol(),
                dir_assets=asset_dir,
                dir_save=self.test_dir,
                stim_movie_format="mp4",
                rec_stim_framerate=30,
                display=dict(window_size=(400, 400), full_screen=False),
                exec=False,
            )

            self.exp = s.exp
            self.exp.calibrator.mm_px = 30 / 400
            s.exp.sig_data_saved.connect(self.waitend)
            s.exp.start_protocol()
            s.exp.app.exec_()
        self.tearDown()
