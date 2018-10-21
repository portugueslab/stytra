import numpy as np
import pandas as pd

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor

from stytra import Stytra
from stytra.stimulation import Protocol
from stytra.stimulation.stimuli import Pause, PybPulseStimulus, VisualStimulus

import tempfile


class Paintme(VisualStimulus):
    def paint(self, p, w, h):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 0, 0)))
        p.drawEllipse(0.0, 0.0, 5, 5)
        p.setBrush(QBrush(QColor(255, 0, 255)))
        p.drawEllipse(100, 400, 5, 5)


class ExternalStimulusProtocol(Protocol):
    def get_stim_sequence(self):
        # Here instead of pause, you will put the Arduino TTL stimulus, which
        # will have to be coded
        return [Paintme(duration=10)]


if __name__ == "__main__":
    save_dir = tempfile.mkdtemp()

    # Here you configure the camera input
    camera_config = dict(type="spinnaker")

    tracking_config = dict(
        embedded=True, tracking_method="angle_sweep", estimator="vigor"
    )

    display_config = dict(full_screen=True)

    # We make a new instance of Stytra with this protocol as the only option
    s = Stytra(
        protocols=[ExternalStimulusProtocol],
        camera_config=camera_config,
        tracking_config=tracking_config,
        display_config=display_config,
        dir_save="D:/stytra",
    )
