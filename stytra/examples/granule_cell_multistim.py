from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter

from stytra import Experiment

from stytra.metadata import MetadataFish,  MetadataLightsheet, MetadataGeneral
from stytra import DataCollector
from stytra.metadata.metalist_gui import MetaListGui

from stytra.stimulation.protocols import SpontActivityProtocol, MultistimulusExp06Protocol

from stytra.triggering import ZmqLightsheetTrigger, PyboardConnection
import json
import git

import multiprocessing

import qdarkstyle


class GcMultistimExperiment(Experiment):
    def __init__(self, app, folder, stim_name):
        super().__init__()
        self.app = app
        multiprocessing.set_start_method('spawn')
        self.pyb = PyboardConnection(com_port='COM3')
        self.zmq_trigger = ZmqLightsheetTrigger(pause=0, tcp_address='tcp://192.168.233.98:5555')
        self.experiment_folder = folder

        # Select a protocol:
        protocol_dict = {'anatomy': SpontActivityProtocol(duration_sec=30, zmq_trigger=self.zmq_trigger),
                         'multistimulus_exp10': MultistimulusExp06Protocol(repetitions=20, mm_px=0.23,
                         shock_args=dict(burst_freq=1, pulse_amp=3., pulse_n=1,
                 pulse_dur_ms=5, pyboard=self.pyb), grating_args=dict(spatial_period=4))}

        try:
            self.protocol = protocol_dict[stim_name]
        except KeyError:
            raise KeyError('Stimulus name must be one of the following: ' +', '.join(protocol_dict.keys()))

        self.finished = False

        # Take care of metadata:
        self.general_data = MetadataGeneral()
        self.fish_data = MetadataFish()
        self.imaging_data = MetadataLightsheet()

        self.metalist_gui = MetaListGui([self.general_data, self.imaging_data,
                                         self.fish_data])

        self.data_collector = DataCollector(self.fish_data, self.imaging_data,
                                            self.general_data,
                                            folder_path=self.experiment_folder,
                                            use_last_val=True)

        try:
            self.set_protocol(protocol_dict[stim_name])
        except KeyError:
            raise KeyError('Stimulus name must be one of the following: ' + ', '.join(protocol_dict.keys()))


        # Create window and layout:
        self.main_layout = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)

        # Show windows:
        self.show()
        self.show_stimulus_screen(True)

    def finishAndSave(self):
        # self.gui_refresh_timer.stop()
        self.data_collector.save(save_csv=False)
        # self.zmq_trigger.stop()
        # self.finishProtocol()
        # self.app.closeAllWindows()
        # self.app.quit()

    def finishProtocol(self):
        # self.camera.join(timeout=1)

        self.finished = True

    def closeEvent(self, QCloseEvent):
        if not self.finished:
            self.finishProtocol()
            self.app.closeAllWindows()
            self.app.quit()

if __name__ == '__main__':
    application = QApplication([])
    application.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    starting_win = StartingWindow(application, ['anatomy', 'multistimulus_exp10'])
    application.exec_()
    print(starting_win.folder)
    print(starting_win.protocol)
    application2 = QApplication([])
    exp = Experiment(application2, starting_win.folder, starting_win.protocol)
    application2.exec_()


