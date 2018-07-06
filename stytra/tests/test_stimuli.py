import unittest
import shutil
import tempfile
import pkg_resources
import numpy as np
from stytra.stimulation.stimuli import FullFieldVisualStimulus,\
    SeamlessGratingStimulus, WindmillStimulus, SeamlessImageStimulus

from stytra.stimulation import Protocol

from stytra import Stytra
import av

class StimulusRenderingProtocol(Protocol):
    name = "protocol_stim"

    def get_stim_sequence(self):
        return [
            FullFieldVisualStimulus(color=(255, 0, 0), clip_rect=(0, 0, 0.5, 0.5), duration=1),
            SeamlessGratingStimulus(grating_angle=np.pi/4, duration=1),
            WindmillStimulus(duration=1),
            SeamlessImageStimulus(background="caustics.png", duration=1)
        ]


class TestStimuli(unittest.TestCase):
    def test_stimulus_rendering(self):
        asset_dir = pkg_resources.resource_filename(__name__, "/test_assets/")
        print(asset_dir)
        s = Stytra(protocols=[StimulusRenderingProtocol], dir_assets=asset_dir,
                   dir_save=asset_dir,
                   stim_movie_format="mp4",
                   rec_stim_every=20)
        s.exp.window_main.widget_control.combo_prot.setCurrentText("protocol_stim")
        s.exp.start_protocol()


