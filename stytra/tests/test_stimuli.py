import unittest
import shutil
import tempfile
import pkg_resources
import numpy as np
import pandas as pd
from stytra.stimulation.stimuli import DynamicLuminanceStimulus, \
    GratingStimulus, WindmillStimulus, SeamlessImageStimulus, InterpolatedStimulus

from PyQt5.QtCore import QTimer

from stytra.stimulation import Protocol

from stytra import Stytra

import shutil

from os import path


class FullFieldProtocol(Protocol):
    name = "full_field"

    def get_stim_sequence(self):
        lum = pd.DataFrame(dict(
            t=[0, 1, 2],
            luminance=[0.0, 1.0, 0.0]

        ))
        return [
            DynamicLuminanceStimulus(df_param=lum, clip_rect=(0.0, 0.0,
                                                              0.5, 0.5)),
            DynamicLuminanceStimulus(df_param=lum, clip_rect=(0.5, 0.5,
                                                              0.5, 0.5)),
        ]


class OKRProtocol(Protocol):
    name = 'okr'

    def get_stim_sequence(self):
        Stim = type("stim",
                    (InterpolatedStimulus, WindmillStimulus), # order is important!
                    {})
        return [
            Stim(df_param=pd.DataFrame(dict(
                t=[0, 2, 4],
                theta=[0, np.pi/8, 0]
            )))
        ]


class GratingProtocol(Protocol):
    name = "grating"

    def get_stim_sequence(self):
        Stim = type("stim", (InterpolatedStimulus, GratingStimulus),
                    dict(theta=np.pi/4))
        return [
            Stim(df_param=pd.DataFrame(dict(t=[0, 2],
                                            vel_x=[10, 10],
                                            vel_y=[0, 5])))
        ]


class SeamlessImageProtocol(Protocol):
    name = "seamless_image"

    def get_stim_sequence(self):
        Stim = type("stim", (SeamlessImageStimulus, InterpolatedStimulus), {})
        return [
            Stim(background="caustics.png",
                 df_param=pd.DataFrame(dict(t=[0, 2],
                               vel_x=[10, 10],
                               vel_y=[0, 5])))
        ]


class GenerateStimuliMovie(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.stopped = False
        self.protocols = []
        self.i_protocol = 0
        self.exp = None

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def waitend(self):
        print("End happened")
        output_folder = (path.dirname(path.dirname(pkg_resources.resource_filename(__name__,
                                                                     ""))) +
                        "/docs/source/_static/")
        shutil.copy(self.exp.folder_name+"/{:03d}_stim_movie.mp4".format(self.i_protocol),
                    output_folder + "stim_movie_" + self.protocols[
                                                        self.i_protocol].name
                                                  + ".mp4")
        self.i_protocol += 1
        if self.i_protocol == len(self.protocols):
            self.exp.wrap_up()
        else:
            self.exp.window_main.widget_control.combo_prot.setCurrentText(
                self.protocols[self.i_protocol].name)
            self.exp.start_protocol()

    def test_stimulus_rendering(self):
        asset_dir = pkg_resources.resource_filename(__name__, "/test_assets/")

        self.protocols = [FullFieldProtocol, OKRProtocol, GratingProtocol,
                          SeamlessImageProtocol]

        s = Stytra(protocols=self.protocols, dir_assets=asset_dir,
                   dir_save=self.test_dir,
                   stim_movie_format="mp4",
                   rec_stim_every=30,
                   exec=False)

        self.exp = s.exp
        self.exp.calibrator.params["mm_px"] = 30/400
        s.exp.window_main.widget_control.combo_prot.setCurrentText("protocol_stim")
        s.exp.protocol_runner.sig_protocol_finished.connect(self.waitend)
        s.exp.start_protocol()
        s.exp.app.exec_()



