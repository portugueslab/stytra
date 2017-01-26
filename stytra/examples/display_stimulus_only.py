from PyQt5.QtWidgets import QApplication, QDialog

from stytra.logging import Logger
from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow

from stytra.triggering import PyboardConnection

import qdarkstyle

class StimulusPrinter:
    def __init__(self, stimuli):
        self.stimuli = stimuli

    def print_stim(self, i):
        print(self.stimuli[i].state())


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

    log = Logger('log.txt', protocol)
    printer = StimulusPrinter(stimuli)
    win_stim_disp = StimulusDisplayWindow(protocol)

    pyb = PyboardConnection(trigger_port)
    pyb.set_pulse_freq(ttl_freq)
    from stytra.triggering import PyboardConnection

    protocol.sig_stim_change.connect(printer.print_stim)
    protocol.sig_protocol_started.connect(pyb.switch_on)
    protocol.sig_protocol_finished.connect(pyb.switch_off)

    win_control = ProtocolControlWindow(app, protocol, win_stim_disp)
    win_control.show()
    win_stim_disp.show()
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_stim_disp.showFullScreen()

    app.exec_()
    log.save()
