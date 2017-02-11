from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget, QSplitter
import qdarkstyle
from stytra.stimulation.stimuli import MovingSeamless, Flash
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import noise_background
import pandas as pd
import numpy as np
from stytra.gui import control_gui, display_gui, camera_display
import stytra.calibration as calibration
import stytra.metadata as metadata
from stytra.paramqt import ParameterGui
from stytra.hardware.video import XimeaCamera, MovingFrameDispatcher, VideoWriter
from stytra.tracking import FishTrackingProcess
from multiprocessing import Queue, Event
from queue import Empty
import datetime
import param as pa



class ProcessingParams(metadata.Metadata):
    blurstd = pa.Integer(3, (0, 5))
    thresh_dif = pa.Integer(20, (0, 100))
    target_area = pa.Integer(450, (0, 700))
    area_tolerance = pa.Integer(320, (0, 700))
    fish_length = pa.Integer(70, (0, 200))
    tail_to_body_ratio = pa.Number(0.8, (0.1, 1))
    n_tail_segments = pa.Integer(6, (1, 20))
    tail_start_from_eye_centre = pa.Number(0.14, (0, 0.5))
    eye_area = pa.Integer(15, (0, 100))
    eye_threshold = pa.Integer(80, (0, 255))


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        experiment_folder = r'D:\vilim\fishrecordings\stytra'
        vidfile = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.avi")

        self.dc = metadata.DataCollector(folder_path=experiment_folder)

        # set up the stimuli
        n_vels = 10
        stim_duration = 15
        refresh_rate = 1/60.

        t_break = np.arange(n_vels+1)*stim_duration

        xs = np.zeros(n_vels+1)
        ys = np.zeros(n_vels+1)
        vel_mean = 50
        vel_std = 5
        angles = np.random.uniform(0, 2*np.pi, n_vels)
        vels = np.random.randn(n_vels)*vel_std+vel_mean

        for i in range(n_vels):
            xs[i+1] = xs[i] + stim_duration * vels[i]*np.cos(angles[i])
            ys[i + 1] = ys[i] + stim_duration * vels[i]*np.sin(angles[i])

        bg = noise_background((800, 800), 8)

        motion = pd.DataFrame(dict(t=t_break, x=xs, y=ys))
        self.protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                                 duration=n_vels*stim_duration)],
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
                                                      diag_queue=self.diag_queue)
        # self.recorder = VideoWriter(experiment_folder + '/' + vidfile,
        #                             self.record_queue, finished_signal=self.finished_sig)

        def_params = dict(blurstd=3,
                          thresh_dif=20,
                          target_area=450,
                          area_tolerance=320,
                          fish_length=70,
                          tail_to_body_ratio=0.8,
                          n_tail_segments=6,
                          tail_start_from_eye_centre=0.14,
                          eye_area=15,
                          eye_aspect=0.9,
                          eye_threshold=80)

        self.tracker = FishTrackingProcess(self.record_queue, self.fish_queue, self.finished_sig, def_params,
                                           diagnostic_queue=self.fish_draw_queue)

        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = display_gui.StimulusDisplayWindow(self.protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.main_layout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_layout)
        self.camera_view = camera_display.CameraViewCalib(self.gui_frame_queue,
                                                          self.control_queue,
                                                          camera_rotation=0)
        self.main_layout.addWidget(self.camera_view)

        self.win_control = control_gui.ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.win_control.refresh_ROI()
        self.main_layout.addWidget(self.win_control)

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()
        self.dc.add_data_source('stimulus', 'display_params',
                                self.win_stim_disp.display_params)
        print(self.win_stim_disp.display_params)
        self.win_stim_disp.update_display_params()
        self.win_control.reset_ROI()

        self.fish_data = metadata.MetadataFish()
        self.stimulus_data = dict(background=bg, motion=motion)
        metawidget = ParameterGui(self.fish_data)
        self.win_control.button_metadata.clicked.connect(metawidget.show)
        self.win_control.button_calibrate.clicked.connect(self.calibrate)
        self.dc.add_data_source('stimulus', 'protocol', self.stimulus_data)
        self.dc.add_data_source('stimulus', 'calibration_to_cam', self.calibrator, 'proj_to_cam')
        self.dc.add_data_source('stimulus', 'calibration_to_proj', self.calibrator, 'cam_to_proj')
        self.dc.add_data_source('stimulus', 'calibration_points', self.calibrator, 'points')
        self.dc.add_data_source('behaviour', 'video_file', vidfile)
        print(self.calibrator.cam_to_proj)
        self.protocol.sig_protocol_started.connect(self.start_rec_sig.set)
        self.protocol.sig_protocol_finished.connect(self.start_rec_sig.clear)
        self.protocol.sig_protocol_finished.connect(self.finishProtocol)

        self.camera.start()
        self.frame_dispatcher.start()
        self.tracker.start()
        self.finished = False
        self.show()

    def calibrate(self):
        try:
            # we steal a frame from the GUI display queue to calibrate
            im = self.gui_frame_queue.get(timeout=1)
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


    # def finishProtocol(self):
    #     self.finished_sig.set()
    #     self.camera.join(timeout=3)
    #     print('Camera joined')
    #     self.frame_dispatcher.join(timeout=3)
    #     print('Frame dispatcher terminated')
    #     timedata = []
    #     while True:
    #         try:
    #             frame, time = self.fish_queue.get(timeout=0.01)
    #             timedelta = (time - self.protocol.t_start).total_seconds()
    #             timedata.append([frame, timedelta])
    #             print('Added a thing')
    #         except Empty:
    #             break
    #
    #     timedata = pd.DataFrame(timedata)
    #     print('{} breaks '.format(len(timedata)))
    #     self.dc.add_data_source('behaviour', 'start_times', timedata)
    #     self.dc.save()
    #
    #     self.tracker.join(timeout=10)
    #     print('Recorder joined')
    #     self.finished = True


    def finishProtocol(self):
        self.finished_sig.set()
        self.camera.join(timeout=3)
        print('Camera joined')
        self.frame_dispatcher.join(timeout=3)
        print('Frame dispatcher terminated')
        detected_fishes = []
        while True:
            try:
                time, fishes = self.fish_queue.get(timeout=0.01)
                timedelta = (time - self.protocol.t_start).total_seconds()
                for fish in fishes:
                    fish['t'] = timedelta
                    detected_fishes.append(fish)
            except Empty:
                break

        print('{} measurements '.format(len(detected_fishes)))
        self.dc.add_data_source('behaviour', 'fish_detected', pd.DataFrame(detected_fishes))
        self.dc.save()

        self.tracker.join(timeout=10)
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
