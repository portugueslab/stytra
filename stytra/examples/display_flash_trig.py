from PyQt5.QtWidgets import QApplication, QDialog

from stytra.logging import Logger
from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.triggering import PyboardConnection
from stytra.triggering import ZmqClient

import qdarkstyle

if __name__ == '__main__':

    trigger_port = 'COM3'
    ttl_freq = 30

    stim_duration = 0.5
    pause_duration = 1
    n_repeats = 5
    flash_color = (255, 0, 0)
    refresh_rate = 1/60.

    # Generate stimulus protocol
    stimuli = []
    for i in range(n_repeats):
        stimuli.append(Flash(duration=stim_duration, color=flash_color))
        stimuli.append(Pause(duration=pause_duration))
    protocol = Protocol(stimuli, refresh_rate)

    # Prepare log (file and display)
    log = Logger('log.txt', protocol)

    #Set up connection with the pyboard
    pyb = PyboardConnection(trigger_port)
    pyb.set_pulse_freq(ttl_freq)

    # Connect start and stop stimulus to start/stop board
    protocol.sig_protocol_started.connect(pyb.switch_on)
    protocol.sig_protocol_finished.connect(pyb.switch_off)

    #Set connection with the 'evil LabView' computer
    zmq_conn = ZmqClient(tcp_address='tcp://192.168.233.156:5555')
    protocol.sig_protocol_started.connect(zmq_conn.send)

    # Prepare control window and window for displaying the  stimulus
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    win_stim_disp = StimulusDisplayWindow(protocol)
    win_control = ProtocolControlWindow(app, protocol, win_stim_disp)
    win_control.show()
    win_stim_disp.show()
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_stim_disp.showFullScreen()

    app.exec_()
    log.save()
