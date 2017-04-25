from PyQt5.QtWidgets import QApplication, QDialog

from stytra.stimulation.stimuli import Pause, Flash, StartAquisition, StopAquisition, PrepareAquisition, ShockStimulus
from stytra.stimulation import Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.triggering import ZmqLightsheetTrigger, PyboardConnection
from stytra.metadata import DataCollector, MetadataFish, MetadataLightsheet, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
import json

import qdarkstyle


if __name__ == '__main__':
    experiment_folder = 'J:/Luigi Petrucco/light_sheet/170420/f1_huc_6s'
    # experiment_folder = '/Users/luigipetrucco/Desktop/metadata/'

    zmq_trigger = ZmqLightsheetTrigger(pause=0, tcp_address='tcp://192.168.233.112:5555')

    flash_color = (255, 255, 255)
    refresh_rate = 60

    ######################################################################################
    ############################
    ## Spontaneus activity
    ###########################
    # stimuli = []
    # stimuli.append(Pause(duration=1))
    # stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    # stimuli.append(Pause(duration=2))
    # stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition
    # stimuli.append(Pause(duration=300)) #change here for duration (in s)
    # ######################################################################################

    ######################################################################################
    ############################
    ### Short protocol flash
    ############################
    stimuli = []
    stimuli.append(Pause(duration=1))
    stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    stimuli.append(Pause(duration=1))
    stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition
    for i in range(10):    #change here for number of stimuli (default: 10 in 5 min (1 every 30 s))
        stimuli.append(Pause(duration=24)) # pre-flash interval
        stimuli.append(Flash(duration=1, color=flash_color)) # flash duration
        stimuli.append(Pause(duration=5)) # post flash interval
    ######################################################################################

    ######################################################################################
    ############################
    ### Pairing protocol
    ############################
    # pyb = PyboardConnection(com_port='COM3')
    # stimuli = []
    # stimuli.append(Pause(duration=1))
    # stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    # stimuli.append(Pause(duration=1))
    # stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition
    # stimuli.append(Pause(duration=24.95))  # pre-shock interval
    # for i in range(50): # change here for number of pairing trials
    #     stimuli.append(Pause(duration=4.))
    #     stimuli.append(Flash(duration=0.95, color=flash_color))  # flash duration
    #     stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
    #                                   pulse_n=1, pulse_dur_ms=5))
    #     stimuli.append(Flash(duration=0.05, color=flash_color))  # flash duration
    #     stimuli.append(Pause(duration=25.0))  # post flash interval
    ######################################################################################

    ######################################################################################
    ############################
    ### Long protocol flash (start and stop 10 seconds of acquisition)
    ############################
    ### Generate stimulus protocol
    # stimuli = []
    # stimuli.append(Pause(duration=1))
    # stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    # stimuli.append(Pause(duration=1))
    # for i in range(50):
    #     stimuli.append(Pause(duration=20)) # inter-stimulus pause
    #     stimuli.append(StartAquisition(zmq_trigger=zmq_trigger)) #start aquisition
    #     stimuli.append(Pause(duration=4)) # pre-flash interval
    #     stimuli.append(Flash(duration=1, color=flash_color)) # flash duration
    #     stimuli.append(Pause(duration=5)) # post flash interval
    #     stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger)) #stop acquisition
    #
    # stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))
    # protocol = Protocol(stimuli, refresh_rate)
    ######################################################################################

    ######################################################################################
    ############################
    ### Short protocol shock (contiunuous acquisition)
    ############################
    # pyb = PyboardConnection(com_port='COM3')
    # stimuli = []
    # stimuli.append(Pause(duration=1))
    # stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    # stimuli.append(Pause(duration=1))
    # stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))  # start aquisition
    # stimuli.append(Pause(duration=24.95))  # pre-shock interval
    # for i in range(10): # change here for number of trials
    #     stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
    #                                   pulse_n=1, pulse_dur_ms=5))
    #     stimuli.append(Pause(duration=30))  # post flash interval
    ######################################################################################




    ######################################################################################
    ############################
    ### Long protocol shock (start and stop 10 seconds of acquition
    ############################
    ###Generate stimulus protocol
    # pyb = PyboardConnection(com_port='COM3')
    #
    # stimuli = []
    # stimuli.append(Pause(duration=1))
    # stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger))
    # stimuli.append(Pause(duration=1))
    # for i in range(50):
    #     stimuli.append(Pause(duration=20)) # inter-stimulus pause
    #     stimuli.append(StartAquisition(zmq_trigger=zmq_trigger)) #start aquisition
    #     stimuli.append(Pause(duration=4.95)) # pre-shock interval
    #     stimuli.append(ShockStimulus(pyboard=pyb, burst_freq=1, pulse_amp=3.5,
    #                                   pulse_n=1, pulse_dur_ms=5))
    #     stimuli.append(Pause(duration=5.05)) # post shock interval
    #     stimuli.append(PrepareAquisition(zmq_trigger=zmq_trigger)) #stop acquisition
    #
    # stimuli.append(StartAquisition(zmq_trigger=zmq_trigger))
    # protocol = Protocol(stimuli, refresh_rate)
    ######################################################################################








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
    # protocol.sig_protocol_started.connect(zmq_trigger.start)
    dict_lightsheet_info = json.loads((zmq_trigger.get_ls_data()).decode('ascii'))
    print(dict_lightsheet_info)
    imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Scanning Type'][:-5].lower())
    imaging_data.set_fix_value('piezo_frequency', dict_lightsheet_info['Piezo Frequency'])
    imaging_data.set_fix_value('piezo_amplitude', abs(dict_lightsheet_info['Piezo Top and Bottom']['1']))
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

