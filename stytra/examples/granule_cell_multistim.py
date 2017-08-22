from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter

from stytra import Experiment

from stytra.metadata import MetadataFish,  MetadataLightsheet, MetadataGeneral
from stytra import DataCollector
from stytra.metadata.metalist_gui import MetaListGui

from stytra.gui.control_gui import StartingWindow

from stytra.stimulation.protocols import SpontActivityProtocol, MultistimulusExp06Protocol

from stytra.triggering import PyboardConnection
import json
import git

import multiprocessing

import qdarkstyle


class GcMultistimExperiment(Experiment):
    def __init__(self, app, folder, stim_name, wait_for_lightsheet=True):
        super().__init__(directory=folder, name=stim_name, app=app)
        self.app = app
        multiprocessing.set_start_method('spawn')
        self.pyb = PyboardConnection(com_port='COM3')
        self.experiment_folder = folder

        # Select a protocol:
        if stim_name == 'anatomy':
            protocol = SpontActivityProtocol(duration_sec=60,
                                             wait_for_lightsheet=wait_for_lightsheet)
        elif stim_name == 'multistimulus_exp10':
            protocol = MultistimulusExp06Protocol(repetitions=20, mm_px=0.23,
                         shock_args=dict(burst_freq=1, pulse_amp=3., pulse_n=1,
                 pulse_dur_ms=5, pyboard=self.pyb),
                                grating_args=dict(spatial_period=4),
                                    wait_for_lightsheet=wait_for_lightsheet)
        else:
            raise ValueError('Stimulus name is not valid')

        self.set_protocol(protocol)
        self.dc.add_data_source('imaging', 'lightsheet_config', protocol, 'lightsheet_config')

        print('The protocol will take {} seconds or {}:{}'.format(protocol.duration,
                                                                  int(protocol.duration)//60,
                                                                  protocol.duration - 60*int(protocol.duration)//60))

        self.finished = False

        # Create window and layout:
        self.main_layout = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)

        # Show windows:
        self.show()
        self.show_stimulus_screen(True)

if __name__ == '__main__':
    application = QApplication([])
    starting_win = StartingWindow(application,
                                  ['anatomy',
                                   'multistimulus_exp10'])
    application.exec_()
    print(starting_win.folder)
    print(starting_win.protocol)
    application2 = QApplication([])
    exp = GcMultistimExperiment(application2, starting_win.folder,
                                starting_win.protocol, wait_for_lightsheet=True)

    application2.exec_()


