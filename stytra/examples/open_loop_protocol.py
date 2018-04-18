import multiprocessing

import qdarkstyle
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
from stytra.metadata.metalist_gui import MetaListGui

from stytra import DataCollector, FrameDispatcher
from stytra.gui.camera_display import CameraTailSelection
from stytra.gui.plots import StreamingPlotWidget
from stytra.gui.protocol_control import ProtocolControlWidget
from stytra.hardware.video import XimeaCamera
from stytra.metadata import MetadataFish, MetadataCamera, MetadataGeneral
from stytra.stimulation import ProtocolRunner
from stytra.stimulation.backgrounds import gratings
from stytra.stimulation.stimuli import Pause, MovingConstantly
from stytra.stimulation.stimulus_display import StimulusDisplayWindow
from stytra.tracking import QueueDataAccumulator
from stytra.tracking.tail import trace_tail_centroid


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        multiprocessing.set_start_method('spawn')

        self.experiment_folder = 'C:/Users/lpetrucco/Desktop/metadata/'
        #self.experiment_folder = '/Users/luigipetrucco/Desktop/metadata/'

        self.finished = False
        self.frame_queue = multiprocessing.Queue()
        self.gui_frame_queue = multiprocessing.Queue()
        self.control_queue = multiprocessing.Queue()
        self.processing_parameter_queue = multiprocessing.Queue()
        self.tail_position_queue = multiprocessing.Queue()
        self.finished_sig = multiprocessing.Event()

        # Take care of metadata:
        self.general_data = MetadataGeneral()
        self.fish_data = MetadataFish()
        self.imaging_data = MetadataLightsheet()
        self.camera_data = MetadataCamera()

        self.roi_dict = {'start_y': 320, 'start_x': 480,
                         'tail_length_y': 0, 'tail_length_x': -400}

        self.metalist_gui = MetaListGui([self.general_data, self.fish_data, self.imaging_data])
        self.data_collector = DataCollector(self.fish_data, self.imaging_data, self.general_data,
                                            self.camera_data, folder_path=self.experiment_folder,
                                            use_last_val=True)
        self.data_collector.add_static_data('tracking', self.roi_dict)

        self.gui_refresh_timer = QTimer()
        self.gui_refresh_timer.setSingleShot(False)

        #self.camera = VideoFileSource(self.frame_queue, self.finished_sig,
        #                                 '/Users/luigipetrucco/Desktop/tail_movement.avi')

        self.camera = XimeaCamera(self.frame_queue, self.finished_sig, self.control_queue)

        self.frame_dispatcher = FrameDispatcher(in_frame_queue=self.frame_queue, gui_queue=self.gui_frame_queue,
                                                processing_function=trace_tail_centroid,
                                                processing_parameter_queue=self.processing_parameter_queue,
                                                finished_signal=self.finished_sig,
                                                output_queue=self.tail_position_queue,
                                                gui_framerate=30, print_framerate=True)

        self.data_acc_tailpoints = QueueDataAccumulator(self.tail_position_queue)

        self.stream_plot = StreamingPlotWidget(data_accumulator=self.data_acc_tailpoints)

        self.camera_viewer = CameraTailSelection(tail_start_points_queue=self.processing_parameter_queue,
                                                 camera_queue=self.gui_frame_queue,
                                                 tail_position_data=self.data_acc_tailpoints,
                                                 update_timer=self.gui_refresh_timer,
                                                 roi_dict=self.roi_dict,
                                                 control_queue=self.control_queue,
                                                 camera_parameters=self.camera_data)

        self.gui_refresh_timer.timeout.connect(self.stream_plot.update)
        self.gui_refresh_timer.timeout.connect(self.data_acc_tailpoints.update_list)
        self.gui_refresh_timer.timeout.connect(self.camera_viewer.update_image)



        # imaging_time = 10
        stim_duration = 20
        refresh_rate = 60.
        initial_pause = 0
        mm_px = 15 / 87
        n_repeats = 1  # (round((imaging_time - initial_pause) / (stim_duration + pause_duration)))

        # Generate stimulus protocol:
        self.stimuli = []
        self.stimuli.append(Pause(duration=initial_pause - 2))
        self.bg = gratings(orientation='horizontal', shape='square',
                           mm_px=mm_px, spatial_period=0.02)
        for i in range(n_repeats):
            # self.stimuli.append(MovingConstantly(background=self.bg, x_vel=0, mm_px=mm_px,
            #                                      duration=stim_duration, monitor_rate=refresh_rate))
            self.stimuli.append(MovingConstantly(background=self.bg, x_vel=10, mm_px=mm_px,
                                                 duration=stim_duration, monitor_rate=refresh_rate))
            # self.stimuli.append(MovingConstantly(background=self.bg, x_vel=0, mm_px=mm_px,
            #                                      duration=stim_duration, monitor_rate=refresh_rate))
            self.stimuli.append(MovingConstantly(background=self.bg, x_vel=-10, mm_px=mm_px,
                                                 duration=stim_duration, monitor_rate=refresh_rate))
        self.protocol = ProtocolRunner(self.stimuli, 1 / refresh_rate)
        self.protocol.sig_protocol_started.connect(self.data_acc_tailpoints.reset)
        self.protocol.sig_protocol_finished.connect(self.finishAndSave)

        # Prepare control window and window for displaying the  stimulus
        # Instantiate display window and control window:
        self.win_stim_disp = StimulusDisplayWindow(self.protocol)
        self.win_control = ProtocolControlWidget(app, self.protocol, self.win_stim_disp)

        # Get info from microscope after setting connection with the LabView computer
        # IMPORTANT: Check IP!!!
        # zmq_trigger = ZmqLightsheetTrigger(pause=initial_pause, tcp_address='tcp://192.168.233.156:5555')
        #
        # protocol.sig_protocol_started.connect(zmq_trigger.start)
        # dict_lightsheet_info = zmq_trigger.get_ls_data()
        # imaging_data.set_fix_value('scanning_profile', dict_lightsheet_info['Sawtooth Wave'])
        # imaging_data.set_fix_value('piezo_frequency', dict_lightsheet_info['Piezo Frequency'])
        # imaging_data.set_fix_value('piezo_amplitude', dict_lightsheet_info['Piezo Top and Bottom']['1'])
        # imaging_data.set_fix_value('frame_rate', dict_lightsheet_info['Triggering']['1'])

        # Metadata window and data collector for saving experiment data:

        self.data_collector.add_static_data('stimulus', 'log', self.protocol.log)
        self.data_collector.add_static_data('stimulus', 'window_pos', self.win_control.widget_view.roi_box.state,
                                            'pos')
        self.data_collector.add_static_data('stimulus', 'window_size',
                                            self.win_control.widget_view.roi_box.state, 'size')
        self.data_collector.add_static_data('camera', 'fish_pos', self.camera_viewer.roi_dict)

        self.win_control.button_metadata.clicked.connect(self.metalist_gui.show_gui)
        self.protocol.sig_protocol_finished.connect(self.data_collector.save)

        # Create window:
        self.main_layout = QSplitter(Qt.Horizontal)

        stim_wid = QSplitter(Qt.Vertical)
        stim_wid.addWidget(self.win_control)

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
        #self.win_stim_disp.windowHandle().setScreen(app.screens()[0])
        #self.win_stim_disp.showFullScreen()
        #self.showMaximized()
        self.show()



    def finishAndSave(self):
        self.gui_refresh_timer.stop()

        self.dataframe = self.data_acc_tailpoints.get_dataframe()

        self.data_collector.add_static_data('behaviour', 'tail_tracking',
                                            self.dataframe)
        self.data_collector.add_static_data('behaviour', 'tail_tracking_start',
                                            self.data_acc_tailpoints.starting_time)

        self.data_collector.save()
        #self.zmq_trigger.stop()
        self.finishProtocol()
        self.app.closeAllWindows()
        self.app.quit()

    def finishProtocol(self):

        self.finished_sig.set()
        # self.camera.join(timeout=1)
        self.camera.terminate()

        self.frame_dispatcher.terminate()
        print('Frame dispatcher terminated')


        print('Camera joined')
        self.gui_refresh_timer.stop()
        print('Timer stopped')

        self.finished = True

    def closeEvent(self, QCloseEvent):
        if not self.finished:
            self.finishProtocol()
            self.app.closeAllWindows()
            self.app.quit()



if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    exp = Experiment(app)
    app.exec_()

