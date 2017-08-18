from PyQt5.QtWidgets import QApplication, QDialog

from stytra.stimulation.stimuli import Pause, ShockStimulus
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.triggering import ZmqLightsheetTrigger
from stytra.metadata import MetadataFish, MetadataLightsheet, MetadataGeneral
from stytra import DataCollector
from stytra.metadata.metalist_gui import MetaListGui
from stytra.hardware.serial import PyboardConnection

import qdarkstyle


if __name__ == '__main__':
    experiment_folder = 'C:/Users/lpetrucco/Desktop/shock_meta/'
    # experiment_folder = '/Users/luigipetrucco/Desktop/metadata/'

    initial_pause = 2
    imaging_time = 180

    shock_freq = 0.1

    pyb = PyboardConnection(com_port='COM3')

    # Generate stimulus protocol
    stimuli = []
    for i in range(5):
        stimuli.append(Pause(duration=2))
        stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
                                     pulse_n=1, pulse_dur_ms=5))
    protocol = Protocol(stimuli)

    # Prepare control window and window for displaying the  stimulus
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # Instantiate control window:
    win_control = ProtocolControlWindow(app, protocol)

    # Take care of metadata:
    general_data = MetadataGeneral()
    fish_data = MetadataFish()
    imaging_data = MetadataLightsheet()

    # Get info from microscope
    # Set connection with the Labview computer
    # zmq_trigger = ZmqLightsheetTrigger(pause=initial_pause, tcp_address='tcp://192.168.236.35:5555')
    # protocol.sig_protocol_started.connect(zmq_trigger.start)
    # dict_lightsheet_info = json.loads((zmq_trigger.get_ls_data()).decode('ascii'))
    # imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Scanning Type'][:-5].lower())
    # imaging_data.set_fix_value('piezo_frequency', dict_lightsheet_info['Piezo Frequency'])
    # #imaging_data.set_fix_value('piezo_amplitude', dict_lightsheet_info['Piezo Top and Bottom']['1'])
    # imaging_data.set_fix_value('frame_rate', dict_lightsheet_info['camera frame capture rate'])

    metalist_gui = MetaListGui([general_data, fish_data, imaging_data])

    data_collector = DataCollector(fish_data, imaging_data, general_data,
                                   folder_path=experiment_folder)
    data_collector.add_data_source('stimulus', 'log', protocol.log)

    win_control.button_metadata.clicked.connect(metalist_gui.show_gui)
    protocol.sig_protocol_finished.connect(data_collector.save)


    # Display windows:
    win_control.show()
    win_control.windowHandle().setScreen(app.screens()[0])
    win_control.refresh_ROI()

    app.exec_()

