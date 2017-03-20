from PyQt5.QtWidgets import QApplication, QDialog

from stytra.stimulation.stimuli import Pause, Flash
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.triggering import ZmqLightsheetTrigger
from stytra.metadata import DataCollector, MetadataFish, MetadataLightsheet, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
import json

import qdarkstyle


if __name__ == '__main__':
    experiment_folder = 'C:/Users/lpetrucco/Desktop/flash_170316_meta/'
    # experiment_folder = '/Users/luigipetrucco/Desktop/metadata/'

    imaging_time = 180

    stim_duration = 1
    pause_duration = 10
    flash_color = (255, 255, 255)
    refresh_rate = 1 / 60.
    initial_pause = 2

    n_repeats = (round((imaging_time - initial_pause) /
                       (stim_duration + pause_duration)))

    # Generate stimulus protocol
    stimuli = []
    stimuli.append(Pause(duration=pause_duration + initial_pause))
    for i in range(n_repeats):
        stimuli.append(Flash(duration=stim_duration, color=flash_color))
        stimuli.append(Pause(duration=pause_duration))
    protocol = Protocol(stimuli, refresh_rate)

    # Prepare control window and window for displaying the  stimulus
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # Instantiate display window and control window:
    win_stim_disp = StimulusDisplayWindow(protocol)
    win_control = ProtocolControlWindow(app, protocol, win_stim_disp)

    # Take care of metadata:
    general_data = MetadataGeneral()
    fish_data = MetadataFish()
    imaging_data = MetadataLightsheet()

    # Get info from microscope
    # Set connection with the Labview computer
    zmq_trigger = ZmqLightsheetTrigger(pause=initial_pause, tcp_address='tcp://192.168.236.35:5555')
    protocol.sig_protocol_started.connect(zmq_trigger.start)
    dict_lightsheet_info = json.loads((zmq_trigger.get_ls_data()).decode('ascii'))
    print(dict_lightsheet_info)
    imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Scanning Type'][:-5].lower())
    imaging_data.set_fix_value('piezo_frequency', dict_lightsheet_info['Piezo Frequency'])
    #imaging_data.set_fix_value('piezo_amplitude', dict_lightsheet_info['Piezo Top and Bottom']['1'])
    imaging_data.set_fix_value('frame_rate', dict_lightsheet_info['camera frame capture rate'])

    metalist_gui = MetaListGui([general_data, fish_data, imaging_data])

    data_collector = DataCollector(fish_data, imaging_data, general_data,
                                   folder_path=experiment_folder)
    data_collector.add_data_source('stimulus', 'log', protocol.log)
    data_collector.add_data_source('stimulus', 'window_pos',
                                   win_control.widget_view.roi_box.state, 'pos')
    data_collector.add_data_source('stimulus', 'window_size',
                                   win_control.widget_view.roi_box.state, 'size')

    win_control.button_metadata.clicked.connect(metalist_gui.show_gui)
    protocol.sig_protocol_finished.connect(data_collector.save)


    # Display windows:
    win_stim_disp.show()
    win_control.show()
    win_control.windowHandle().setScreen(app.screens()[0])
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_control.widget_view.repaint()
    win_stim_disp.showFullScreen()
    win_control.refresh_ROI()

    app.exec_()

