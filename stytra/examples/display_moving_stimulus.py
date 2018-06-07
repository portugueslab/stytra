import datetime
from multiprocessing import Queue, Event
from queue import Empty

import numpy as np
import pandas as pd
import qdarkstyle
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, \
    QSplitter, QProgressBar

import stytra.calibration as calibration
import stytra.collectors
from stytra import MovingFrameDispatcher
from stytra.data_log import MetaListGui
from stytra.gui import protocol_control, camera_display
from stytra.hardware.video import XimeaCamera, VideoWriter
from stytra.stimulation import ProtocolRunner, stimulus_display
from stytra.stimulation.backgrounds import existing_file_background
from stytra.stimulation.stimuli import MovingSeamless


def make_moving_protocol(n_vels=240*3, stim_duration=5,
                         vel_mean=30, vel_std=5):
    t_break = np.arange(n_vels + 1) * stim_duration

    angles = np.random.uniform(0, 2 * np.pi, n_vels)
    vels = np.random.randn(n_vels) * vel_std + vel_mean

    coords = np.zeros((n_vels + 1, 2))
    trigs = [np.cos, np.sin]

    for i_coord, trig in zip(range(2), trigs):
        for i in range(n_vels):
            coords[(i + 1), i_coord] = coords[i, i_coord] + stim_duration * vels[i] * trig(angles[i])

    return pd.DataFrame(dict(t=t_break,
                             x=coords[:, 0],
                             y=coords[:, 1]))


def make_moving_pausing_protocol(n_vels=240 * 3, stim_duration=5, pause_duration=5,
                                 vel_mean=30, vel_std=5):
    t_break = np.tile(np.arange(n_vels)*(stim_duration+pause_duration), (2, 1)).reshape((-1), order='F')
    t_break[1::2] += stim_duration
    t_break = np.concatenate([t_break, [t_break[-1]+pause_duration]])

    angles = np.random.uniform(0, 2 * np.pi, n_vels)
    vels = np.random.randn(n_vels) * vel_std + vel_mean

    coords = np.zeros((n_vels * 2 + 1,2))
    trigs = [np.cos, np.sin]

    for i_coord, trig in zip(range(2), trigs):
        for i in range(n_vels):
            coords[2 * (i + 1), i_coord] = coords[2 * i, i_coord] + stim_duration * vels[i] * trig(angles[i])

    coords[1::2] = coords[2::2]

    return pd.DataFrame(dict(t=t_break,
                             x=coords[:, 0],
                             y=coords[:, 1]))


def make_spinning_protocol(n_vels=100, stim_duration=10, pause_duration=5,
                                 vel_mean=0.5, vel_std=0.35):
    t_break = np.tile(np.arange(n_vels) * (stim_duration + pause_duration), (2, 1)).reshape((-1), order='F')
    t_break[1::2] += stim_duration
    t_break = np.concatenate([t_break, [t_break[-1] + pause_duration]])

    vels = np.random.randn(n_vels) * vel_std + vel_mean

    thetas = np.zeros((n_vels * 2 + 1))

    for i in range(n_vels):
        thetas[2 * (i + 1)] = thetas[2 * i] + stim_duration * vels[i] * np.random.choice([-1, 1])

    thetas[1::2] = thetas[2::2]

    return pd.DataFrame(dict(t=t_break,
                            theta=thetas))


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        experiment_folder = r'D:\vilim\fishrecordings\stytra\pausing'
        self.expid = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        vidfile = self.expid+'.avi'

        general_data = data_log.MetadataGeneral()
        fish_data = data_log.MetadataFish()

        self.im_filename = r"C:\Users\vilim\experimental\underwater\66_underwater beach sand texture-seamless.jpg"

        self.camera_parameters = data_log.MetadataCamera()

        self.dc = stytra.collectors.DataCollector(folder_path=experiment_folder)

        self.dc.add_static_data(fish_data)
        self.dc.add_static_data(general_data)
        self.dc.add_static_data(self.camera_parameters, use_last_val=True)

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        # set up the stimuli
        refresh_rate = 1/60.

        motion = make_moving_pausing_protocol(n_vels=500, stim_duration=5, pause_duration=10)
        self.protocol_duration = motion.t.iat[-1]

        bg = existing_file_background(self.im_filename)

        self.protocol = ProtocolRunner([MovingSeamless(background=bg, motion=motion,
                                                       duration=motion.t.iat[-1])],
                                       dt=refresh_rate)


        # queues for interprocess communication
        self.frame_queue = Queue()
        self.control_queue = Queue()
        self.gui_frame_queue = Queue()
        self.record_queue = Queue()
        self.framestart_queue = Queue()
        self.fish_queue = Queue()
        self.fish_draw_queue = Queue()

        self.finished_sig = Event()
        self.start_rec_sig = Event()
        self.camera = XimeaCamera(self.frame_queue, self.finished_sig, self.control_queue)
        self.frame_dispatcher = MovingFrameDispatcher(self.frame_queue,
                                                      self.gui_frame_queue,
                                                      self.finished_sig,
                                                      output_queue=self.record_queue,
                                                      framestart_queue=self.framestart_queue,
                                                      signal_start_rec=self.start_rec_sig,
                                                      gui_framerate=30)

        self.recorder = VideoWriter(experiment_folder + '/' + vidfile,
                                     self.record_queue, finished_signal=self.finished_sig)

        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = stimulus_display.StimulusDisplayWindow(self.protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.main_layout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_layout)
        self.camera_view = camera_display.CameraViewCalib(self.gui_frame_queue,
                                                          self.control_queue,
                                                          update_timer=self.gui_timer,
                                                          camera_rotation=0,
                                                          camera_parameters=self.camera_parameters)
        self.main_layout.addWidget(self.camera_view)

        self.win_control = protocol_control.ProtocolControlWidget(app, self.protocol, self.win_stim_disp)
        self.win_control.refresh_ROI()
        self.win_control.button_show_calib.clicked.connect(self.config_cam_calib)
        self.main_layout.addWidget(self.win_control)
        self.prog_bar = QProgressBar()
        # self.gui_timer.timeout.connect(self.update_progress)

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()
        self.dc.add_static_data('stimulus', 'display_params',
                                self.win_stim_disp.params)
        self.win_stim_disp.update_display_params()
        self.win_control.reset_ROI()

        self.metalist_gui = MetaListGui([general_data, fish_data])

        self.stimulus_data = dict(background=bg, motion=motion)
        self.win_control.button_metadata.clicked.connect(self.metalist_gui.show_gui)
        self.win_control.button_calibrate.clicked.connect(self.calibrate)
        self.dc.add_static_data('stimulus', 'image_file', self.im_filename)
        self.dc.add_static_data('stimulus', 'protocol', self.stimulus_data, use_last_val=False)
        self.dc.add_static_data('stimulus', 'calibration_to_cam', self.calibrator, 'proj_to_cam')
        self.dc.add_static_data('stimulus', 'calibration_to_proj', self.calibrator, 'cam_to_proj')
        self.dc.add_static_data('stimulus', 'calibration_points', self.calibrator, 'points')
        self.dc.add_static_data('behaviour', 'video_file', vidfile)

        self.protocol.sig_protocol_started.connect(self.start_rec_sig.set)
        self.protocol.sig_protocol_finished.connect(self.start_rec_sig.clear)
        self.protocol.sig_protocol_finished.connect(self.finishProtocol)

        self.protocol.sig_timestep.connect(self.update_progress)

        self.camera.start()
        self.frame_dispatcher.start()
        self.recorder.start()
        self.gui_timer.start()
        self.finished = False
        self.show()

    # def update_progress(self):
    #     time_elapsed = datetime.datetime.now()-self.protocol.t_start
    #     self.prog_bar.setValue(int(time_elapsed*100/self.protocol_duration))

    def config_cam_calib(self):
        pass
        # TODO change camera settings when calibrating

    def update_progress(self):
        finished = (datetime.datetime.now() - self.protocol.t_start).total_seconds()/self.protocol_duration
        self.win_control.progbar_protocol.setValue(int(finished*100))

    def calibrate(self):
        try:
            # we steal a frame from the GUI display queue to calibrate
            time, im = self.gui_frame_queue.get(timeout=1)
            try:
                self.calibrator.find_transform_matrix(im)
                self.win_control.widget_view.display_calibration_pattern(self.calibrator)
                print(self.calibrator.points_cam)
                self.camera_view.show_calibration(self.calibrator)
            except calibration.CalibrationException:
                print('No new transform matrix')
                if self.calibrator.proj_to_cam is not None and self.calibrator.points is not None:
                    self.camera_view.show_calibration(self.calibrator)
        except Empty:
            pass

    def finishProtocol(self, isfinished):
        self.finished_sig.set()
        self.camera.join(timeout=3)
        print('Camera joined')
        self.frame_dispatcher.join(timeout=3)
        print('Frame dispatcher terminated')
        timedata = []
        print(self.framestart_queue.qsize())
        while True:
            try:
                time = self.framestart_queue.get(timeout=0.1)
                timedelta = (time - self.protocol.t_start).total_seconds()
                timedata.append([timedelta])
            except Empty:
                break

        timedata = np.array(timedata)
        print('{} breaks '.format(len(timedata)))
        self.dc.add_static_data('behaviour', 'frame_times', timedata)
        self.dc.save(self.expid)

        self.recorder.join(timeout=600)
        print('Recorder joined')
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
