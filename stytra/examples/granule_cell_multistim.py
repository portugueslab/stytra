from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter

from stytra.stimulation.protocols import SpontActivityProtocol, ShockProtocol, FlashProtocol, FlashShockProtocol, MultistimulusExp06Protocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow, StartingWindow
from stytra.metadata import DataCollector, MetadataFish, MetadataCamera, MetadataLightsheet, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
from stytra.tracking.tail import detect_tail_embedded
from stytra.gui.plots import StreamingPlotWidget
from stytra.gui.camera_display import CameraTailSelection
from stytra.hardware.video import XimeaCamera, FrameDispatcher
from stytra.tracking import DataAccumulator
from stytra.triggering import ZmqLightsheetTrigger, PyboardConnection
import json
import git


import multiprocessing

import qdarkstyle


class Experiment(QMainWindow):
    def __init__(self, app, folder, stim_name):
        super().__init__()
        self.app = app
        multiprocessing.set_start_method('spawn')
        self.pyb = PyboardConnection(com_port='COM3')
        self.zmq_trigger = ZmqLightsheetTrigger(pause=0, tcp_address='tcp://192.168.233.98:5555')
        self.experiment_folder = folder

        # Editable part #############################################################################################
        #############################################################################################################
        # Experiment folder:
        # self.experiment_folder = 'C:/Users/lpetrucco/Desktop'
        run_only_committed = True
        #############################################################################################################
        # End editable part #########################################################################################
        # Fixed factor for converting piezo voltages to microns; an half FOV of 5 results in 400 microns scanning, so:
        piezo_amp_conversion = 400 / 5

        # Select a protocol:
        protocol_dict = {'anatomy': (SpontActivityProtocol(duration_sec=30, zmq_trigger=self.zmq_trigger),
                                     240),
                         'multistimulus_exp10': (MultistimulusExp06Protocol(repetitions=20, mm_px=0.23,
                             zmq_trigger=self.zmq_trigger,
                         shock_args=dict(burst_freq=1, pulse_amp=3., pulse_n=1,
                 pulse_dur_ms=5, pyboard=self.pyb), grating_args=dict(spatial_period=4)), 100)}

        try:
            self.protocol = protocol_dict[stim_name][0]
        except KeyError:
            raise KeyError('Stimulus name must be one of the following: ' +', '.join(protocol_dict.keys()))

        self.finished = False

        # Take care of metadata:
        self.general_data = MetadataGeneral()
        self.fish_data = MetadataFish()
        self.imaging_data = MetadataLightsheet()

        self.metalist_gui = MetaListGui([self.general_data, self.imaging_data,  self.fish_data])

        self.data_collector = DataCollector(self.fish_data, self.imaging_data, self.general_data,
                                            folder_path=self.experiment_folder,
                                            use_last_val=True)

        try:
            self.protocol = protocol_dict[stim_name][0]
        except KeyError:
            raise KeyError('Stimulus name must be one of the following: spontaneous, flash, shock, pairing')


        repo = git.Repo(search_parent_directories=True)
        git_hash = repo.head.object.hexsha
        self.data_collector.add_data_source('general', 'git_hash', git_hash)
        self.data_collector.add_data_source('general', 'program_name', __file__)

        if len(repo.git.diff('HEAD~1..HEAD', name_only=True)) > 0 and run_only_committed:
            print('The following files contain uncommitted changes:')
            print(repo.git.diff('HEAD~1..HEAD', name_only=True))
            raise PermissionError('The project has to be committed before starting!')

        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)


        self.protocol.sig_protocol_finished.connect(self.finishAndSave)

        # Prepare control window and window for displaying the  stimulus
        # Instantiate display window and control window:
        self.win_stim_disp = StimulusDisplayWindow(self.protocol)

        self.win_control = ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.data_collector.add_data_source('stimulus', 'window_pos',
                                            self.win_control.widget_view.roi_box.state, 'pos')
        self.data_collector.add_data_source('stimulus', 'window_size',
                                            self.win_control.widget_view.roi_box.state, 'size')
        self.data_collector.add_data_source('stimulus', 'log', self.protocol.log)

        dict_lightsheet_info = json.loads((self.zmq_trigger.get_ls_data()).decode('ascii'))
        self.imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Scanning Type'][:-5].lower())
        piezo_amp = abs(dict_lightsheet_info['Piezo Top and Bottom']['1'])
        piezo_freq = dict_lightsheet_info['Piezo Frequency']
        imaging_framerate = dict_lightsheet_info['camera frame capture rate']
        if imaging_framerate == 0:
            imaging_framerate = 1;
        print('Step size on z:' + str(piezo_amp_conversion*piezo_amp*(piezo_freq/imaging_framerate)) + ' um')
        self.imaging_data.set_fix_value('piezo_frequency', piezo_freq)
        self.imaging_data.set_fix_value('piezo_amplitude', piezo_amp)
        self.imaging_data.set_fix_value('frame_rate', imaging_framerate)
        self.imaging_data.set_fix_value('dz', (piezo_amp_conversion*piezo_amp*(piezo_freq/imaging_framerate)))
        self.imaging_data.set_fix_value('n_frames', protocol_dict[stim_name][1])
        print(dict_lightsheet_info)
        print('The experiment will last: {:.2f} seconds'.format(self.protocol.get_duration()))
        print('And require {} frames'.format(int(self.protocol.get_duration()*imaging_framerate)))
        self.win_control.button_metadata.clicked.connect(self.metalist_gui.show_gui)
        self.win_control.refresh_ROI()

        # Create window:
        self.main_layout = QSplitter(Qt.Horizontal)

        stim_wid = QSplitter(Qt.Vertical)
        stim_wid.addWidget(self.win_control)

        self.main_layout.addWidget(stim_wid)
        self.setCentralWidget(self.main_layout)

        # Show windows:
        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()
        self.show()

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


