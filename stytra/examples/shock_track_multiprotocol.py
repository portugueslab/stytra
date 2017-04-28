from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter

from stytra.stimulation.protocols import SpontActivityProtocol, ShockProtocol, FlashProtocol, FlashShockProtocol
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow, ProtocolSelectorWidget
from stytra.metadata import DataCollector, MetadataFish, MetadataCamera, MetadataLightsheet, MetadataGeneral
from stytra.metadata.metalist_gui import MetaListGui
from stytra.tracking.tail import detect_tail_embedded
from stytra.gui.plots import StreamingPlotWidget
from stytra.gui.camera_display import CameraTailSelection
from stytra.hardware.video import XimeaCamera, FrameDispatcher, VideoFileSource
from stytra.tracking import DataAccumulator
from stytra.triggering import ZmqLightsheetTrigger, PyboardConnection
import json


import multiprocessing

import qdarkstyle


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        multiprocessing.set_start_method('spawn')

        self.experiment_folder = 'C:/Users/lpetrucco/Desktop/provashock'
        #self.experiment_folder = '/Users/luigipetrucco/Desktop/metadata/'

        self.finished = False
        self.frame_queue = multiprocessing.Queue()
        self.gui_frame_queue = multiprocessing.Queue()
        self.control_queue = multiprocessing.Queue()
        self.processing_param_queue = multiprocessing.Queue()
        self.tail_pos_queue = multiprocessing.Queue()
        self.finished_sig = multiprocessing.Event()

        # Take care of metadata:
        self.general_data = MetadataGeneral()
        self.fish_data = MetadataFish()
        self.imaging_data = MetadataLightsheet()
        self.camera_data = MetadataCamera()

        self.metalist_gui = MetaListGui([self.general_data, self.imaging_data,  self.fish_data])

        self.data_collector = DataCollector(self.fish_data, self.imaging_data, self.general_data,
                                            self.camera_data, folder_path=self.experiment_folder,
                                            use_last_val=True)


        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)

        # self.camera = VideoFileSource(self.frame_queue, self.finished_sig,
        #                                 '/Users/luigipetrucco/Desktop/tail_movement.avi')

        self.camera = XimeaCamera(self.frame_queue, self.finished_sig, self.control_queue)

        self.frame_dispatcher = FrameDispatcher(frame_queue=self.frame_queue, gui_queue=self.gui_frame_queue,
                                                processing_function=detect_tail_embedded,
                                                processing_parameter_queue=self.processing_param_queue,
                                                finished_signal=self.finished_sig, output_queue=self.tail_pos_queue,
                                                gui_framerate=30, print_framerate=False)

        self.data_acc_tailpoints = DataAccumulator(self.tail_pos_queue)

        self.stream_plot = StreamingPlotWidget(data_accumulator=self.data_acc_tailpoints)

        self.roi_dict = {'start_y': 320, 'start_x': 480, 'length_y': 0, 'length_x': -400}

        self.data_collector.add_data_source('tracking', self.roi_dict)

        self.camera_viewer = CameraTailSelection(tail_start_points_queue=self.processing_param_queue,
                                                 camera_queue=self.gui_frame_queue,
                                                 tail_position_data=self.data_acc_tailpoints,
                                                 update_timer=self.gui_refresh_timer,
                                                 roi_dict=self.roi_dict,
                                                 control_queue=self.control_queue,
                                                 camera_parameters=self.camera_data)

        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(self.data_acc_tailpoints.update_list)
        self.gui_refresh_timer.timeout.connect(self.camera_viewer.update_image)

        self.pyb = PyboardConnection(com_port='COM3')

        zmq_trigger = ZmqLightsheetTrigger(pause=0, tcp_address='tcp://192.168.236.163:5555')

        self.protocol_list = [SpontActivityProtocol(duration=5, zmq_trigger=zmq_trigger),
                              FlashProtocol(repetitions=2, period_sec=2, zmq_trigger=zmq_trigger),
                              ShockProtocol(repetitions=2, period_sec=10, zmq_trigger=zmq_trigger, pyb=self.pyb)]

        self.protocol = self.protocol_list[0]
        self.protocol.print()

        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)
        self.protocol.sig_protocol_finished.connect(self.finishAndSave)

        # Prepare control window and window for displaying the  stimulus
        # Instantiate display window and control window:
        self.win_stim_disp = StimulusDisplayWindow(self.protocol)

        self.win_control = ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.data_collector.add_data_source('stimulus', 'window_pos',
                                       self.win_control.widget_view.roi_box.state, 'pos')
        self.data_collector.add_data_source('stimulus', 'window_size',
                                       self.win_control.widget_view.roi_box.state, 'size')

        dict_lightsheet_info = json.loads((zmq_trigger.get_ls_data()).decode('ascii'))
        print(dict_lightsheet_info)
        self.imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Scanning Type'][:-5].lower())
        self.imaging_data.set_fix_value('piezo_frequency', dict_lightsheet_info['Piezo Frequency'])
        self.imaging_data.set_fix_value('piezo_amplitude', abs(dict_lightsheet_info['Piezo Top and Bottom']['1']))
        self.imaging_data.set_fix_value('frame_rate', dict_lightsheet_info['camera frame capture rate'])

        # data collector for saving experiment data:
        self.set_datacollector()

        self.win_control.button_metadata.clicked.connect(self.metalist_gui.show_gui)

        self.protocol_selector = ProtocolSelectorWidget(self.app, self.protocol_list)
        self.protocol_selector.change_signal.connect(self.switch_protocol)

        # Create window:
        self.main_layout = QSplitter(Qt.Horizontal)

        stim_wid = QSplitter(Qt.Vertical)
        stim_wid.addWidget(self.win_control)
        stim_wid.addWidget(self.protocol_selector)

        fish_wid = QSplitter(Qt.Vertical)
        fish_wid.addWidget(self.camera_viewer)
        fish_wid.addWidget(self.stream_plot)

        self.main_layout.addWidget(stim_wid)
        self.main_layout.addWidget(fish_wid)
        self.setCentralWidget(self.main_layout)

        # Start dispatcher:
        self.camera.start()
        self.frame_dispatcher.start()
        self.gui_refresh_timer.start()

        # Show windows:
        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()
        self.show()


    def finishAndSave(self):
        #self.gui_refresh_timer.stop()

        self.dataframe = self.data_acc_tailpoints.get_dataframe()
        self.data_collector.add_data_source('behaviour', 'tail_tracking',
                                            self.dataframe)
        self.data_collector.add_data_source('behaviour', 'tail_tracking_start',
                                            self.data_acc_tailpoints.starting_time)

        self.data_collector.save()
        self.data_acc_tailpoints.reset()
        #self.zmq_trigger.stop()
        #self.finishProtocol()
        #self.app.closeAllWindows()
        #self.app.quit()


    def finishProtocol(self):
        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()
        print('Camera joined')
        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')
        self.gui_refresh_timer.stop()
        print('Timer stopped')

        self.finished = True

    def closeEvent(self, QCloseEvent):
        if not self.finished:
            self.finishProtocol()
            self.app.closeAllWindows()
            self.app.quit()

    def switch_protocol(self):
        i = self.protocol_selector.index
        self.protocol = self.protocol_list[i]
        self.win_control.set_protocol(self.protocol)
        #self.general_data.set_fix_value('experiment_name', self.protocol.name)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)
        self.protocol.sig_protocol_finished.connect(self.finishAndSave)
        self.protocol.print()

        self.set_datacollector()

    def set_datacollector(self):
        self.data_collector = DataCollector(self.fish_data, self.imaging_data, self.general_data,
                                            self.camera_data, folder_path=self.experiment_folder,
                                            use_last_val=True)
        self.data_collector.add_data_source('tracking', self.roi_dict)
        self.data_collector.add_data_source('stimulus', 'log', self.protocol.log)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    exp = Experiment(app)
    app.exec_()

