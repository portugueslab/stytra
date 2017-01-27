from PyQt5.QtWidgets import QApplication, QDialog

from stytra.logging import StimulusLogger
from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.metadata import MetadataFish

import qdarkstyle


if __name__ == '__main__':

    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    trigger_port = 'COM3'
    ttl_freq = 30

    stim_duration = 0.5
    pause_duration = 1
    n_repeats = 3
    flash_color = (255, 0, 0)
    refresh_rate = 1/60.

    stimuli = []

    for i in range(n_repeats):
        stimuli.append(Flash(duration=stim_duration, color=flash_color))
        stimuli.append(Pause(duration=pause_duration))

    protocol = Protocol(stimuli, refresh_rate)


    win_stim_disp = StimulusDisplayWindow(protocol)
    win_control = ProtocolControlWindow(app, protocol, win_stim_disp)

    logger = StimulusLogger(protocol, log_print=True)
    fish_meta = MetadataFish()

    win_control.show()
    win_stim_disp.show()
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_stim_disp.showFullScreen()

    app.exec_()
