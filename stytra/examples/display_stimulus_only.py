from PyQt5.QtWidgets import QApplication, QDialog

from stytra.logging import Logger
from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow


class StimulusPrinter:
    def __init__(self, stimuli):
        self.stimuli = stimuli

    def print_stim(self, i):
        print(self.stimuli[i].state())


if __name__ == '__main__':

    app = QApplication([])

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

    log = Logger('log.txt', protocol)
    printer = StimulusPrinter(stimuli)
    win = StimulusDisplayWindow(stimuli)

    protocol.sig_stim_change.connect(printer.print_stim)

    protocol.sig_timestep.connect(win.display_stimulus)

    win_control = ProtocolControlWindow(app, protocol, win)
    win_control.show()
    win.show()

    app.exec_()
    log.save()
