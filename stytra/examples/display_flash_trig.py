from PyQt5.QtWidgets import QApplication, QDialog

from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.triggering import ZmqClient
from stytra.metadata import DataCollector, MetadataFish, MetadataLightsheet, MetadataGeneral

import qdarkstyle

if __name__ == '__main__':

    experiment_folder = '/Users/luigipetrucco/Desktop/meta'

    stim_duration = 0.5
    pause_duration = 1
    n_repeats = 3
    flash_color = (255, 0, 0)
    refresh_rate = 1/60.

    # Generate stimulus protocol
    stimuli = []
    for i in range(n_repeats):
        stimuli.append(Flash(duration=stim_duration, color=flash_color))
        stimuli.append(Pause(duration=pause_duration))
    protocol = Protocol(stimuli, refresh_rate)

    #Set connection with the 'evil LabView' computer
    #zmq_conn = ZmqClient(tcp_address='tcp://192.168.233.156:5555')
    #protocol.sig_protocol_started.connect(zmq_conn.send)

    # Prepare control window and window for displaying the  stimulus
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # Instantiate display window and control window:
    win_stim_disp = StimulusDisplayWindow(protocol)
    win_control = ProtocolControlWindow(app, protocol, win_stim_disp)

    # Take care of metadata:
    general_data = MetadataGeneral(experiment_name='only_flashes', experimenter_name='Luigi Petrucco')
    fish_data = MetadataFish()
    imaging_data = MetadataLightsheet()
    imaging_data.set_fix_value('scanning_profile', 'sawtooth')
    imaging_data.set_fix_value('piezo_frequency', 1)
    imaging_data.set_fix_value('piezo_amplitude', 1)

    provadict = dict(a=8, b=9)
    print(win_control.widget_view.roi_box.state)
    data_collector = DataCollector(fish_data,
                                   imaging_data,
                                   general_data,
                                   ('stimulus', provadict),
                                   ('stimulus', 'log', protocol.log),
                                   ('stimulus', 'window_pos', win_control.widget_view.roi_box.state, 'pos'),
                                   ('stimulus', 'window_size', win_control.widget_view.roi_box.state, 'size'),
                                   folder_path=experiment_folder)

    print(win_control.widget_view.roi_box.state)
    win_control.button_metadata.clicked.connect(fish_data.show_gui)
    protocol.sig_protocol_finished.connect(data_collector.save)


    # Display windows:
    win_stim_disp.show()
    win_control.show()
    win_control.windowHandle().setScreen(app.screens()[0])
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_control.widget_view.repaint()
    win_stim_disp.showFullScreen()
    win_control.update_ROI()

    app.exec_()

