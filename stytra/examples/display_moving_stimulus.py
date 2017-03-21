from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow,\
    QWidget, QSplitter, QProgressBar
import qdarkstyle
from stytra.stimulation.stimuli import MovingSeamless
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import noise_background, poisson_disk_background, existing_file_background
import pandas as pd
import numpy as np
from stytra.gui import control_gui, display_gui, camera_display
import stytra.calibration as calibration
import stytra.metadata as metadata
from stytra.metadata.metalist_gui import MetaListGui
from paramqt import ParameterGui
from stytra.hardware.video import XimeaCamera, MovingFrameDispatcher, VideoWriter
from stytra.tracking import FishTrackingProcess
from multiprocessing import Queue, Event
from queue import Empty
from PyQt5.QtCore import QTimer
import datetime
import param as pa


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


def make_spinning_protocol(n_vels=500, stim_duration=10, pause_duration=5,
                                 vel_mean=0.6, vel_std=0.4):
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

        general_data = metadata.MetadataGeneral()
        fish_data = metadata.MetadataFish()

        self.im_filename = r"C:\Users\vilim\experimental\underwater\66_underwater beach sand texture-seamless.jpg"

        self.camera_parameters = metadata.MetadataCamera()

        self.dc = metadata.DataCollector(folder_path=experiment_folder)

        self.dc.add_data_source(fish_data)
        self.dc.add_data_source(general_data)
        self.dc.add_data_source(self.camera_parameters, use_last_val=True)

        self.gui_timer = QTimer()
        self.gui_timer.setSingleShot(False)

        # set up the stimuli

        refresh_rate = 1/60.

        motion = make_spinning_protocol()
        self.protocol_duration = motion.t.iat[-1]

        bg = existing_file_background(self.im_filename)

        self.protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                                 duration=motion.t.iat[-1])],
                                                 dt=refresh_rate)

        # queues for interprocess communication
        self.frame_queue = Queue()
        self.control_queue = Queue()
        self.gui_frame_queue = Queue()
        self.record_queue = Queue()
        self.diag_queue = Queue()
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
                                                      diag_queue=self.diag_queue,
                                                      gui_framerate=30)

        self.recorder = VideoWriter(experiment_folder + '/' + vidfile,
                                     self.record_queue, finished_signal=self.finished_sig)

        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = display_gui.StimulusDisplayWindow(self.protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.main_layout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_layout)
        self.camera_view = camera_display.CameraViewCalib(self.gui_frame_queue,
                                                          self.control_queue,
                                                          camera_rotation=0,
                                                          camera_parameters=self.camera_parameters)
        self.gui_timer.timeout.connect(self.camera_view.update_image)
        self.main_layout.addWidget(self.camera_view)

        self.win_control = control_gui.ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.win_control.refresh_ROI()
        self.win_control.button_show_calib.clicked.connect(self.config_cam_calib)
        self.main_layout.addWidget(self.win_control)
        self.prog_bar = QProgressBar()
        # self.gui_timer.timeout.connect(self.update_progress)

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()
        self.dc.add_data_source('stimulus', 'display_params',
                                self.win_stim_disp.display_params)
        self.win_stim_disp.update_display_params()
        self.win_control.reset_ROI()

        self.metalist_gui = MetaListGui([general_data, fish_data])

        self.stimulus_data = dict(background=bg, motion=motion)
        self.win_control.button_metadata.clicked.connect(self.metalist_gui.show_gui)
        self.win_control.button_calibrate.clicked.connect(self.calibrate)
        self.dc.add_data_source('stimulus', 'image_file', self.im_filename)
        self.dc.add_data_source('stimulus', 'protocol', self.stimulus_data, use_last_val=False)
        self.dc.add_data_source('stimulus', 'calibration_to_cam', self.calibrator, 'proj_to_cam')
        self.dc.add_data_source('stimulus', 'calibration_to_proj', self.calibrator, 'cam_to_proj')
        self.dc.add_data_source('stimulus', 'calibration_points', self.calibrator, 'points')
        self.dc.add_data_source('behaviour', 'video_file', vidfile)

        self.protocol.sig_protocol_started.connect(self.start_rec_sig.set)
        self.protocol.sig_protocol_finished.connect(self.start_rec_sig.clear)
        self.protocol.sig_protocol_finished.connect(self.finishProtocol)

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

    def finishProtocol(self):
        self.finished_sig.set()
        self.camera.join(timeout=3)
        print('Camera joined')
        self.frame_dispatcher.join(timeout=3)
        print('Frame dispatcher terminated')
        timedata = []

        while True:
            try:
                time = self.framestart_queue.get(timeout=0.01)
                timedelta = (time - self.protocol.t_start).total_seconds()
                timedata.append([timedelta])
            except Empty:
                break

        timedata = np.array(timedata)
        print('{} breaks '.format(len(timedata)))
        self.dc.add_data_source('behaviour', 'frame_times', timedata)
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
