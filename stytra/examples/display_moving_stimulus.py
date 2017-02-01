from PyQt5.QtWidgets import QApplication, QHBoxLayout, QDialog
import qdarkstyle
from stytra.stimulation.stimuli import MovingSeamless, Flash
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import noise_background
import pandas as pd
import numpy as np
from stytra.gui import control_gui, display_gui, camera_display
from functools import partial
import stytra.calibration as calibration
import stytra.metadata as metadata
from stytra.paramqt import ParameterGui
import cv2
import pyqtgraph as pg
from stytra.hardware.cameras import XimeaCamera, FrameDispatcher
from multiprocessing import Queue, Event

class Experiment:

    def __init__(self):
        app = QApplication([])
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        n_vels = 10
        stim_duration = 10
        refresh_rate =1/60.

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

        bg = noise_background((100, 100), 10)

        motion = pd.DataFrame(dict(t=t_break, x=xs, y=ys))
        protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                            duration=n_vels*stim_duration)],
                            dt=refresh_rate)

        protocol.sig_protocol_started.connect(self.start_external)

        # camera stuff
        self.frame_queue = Queue()
        self.control_queue = Queue()
        self.gui_frame_queue = Queue()
        self.finished_sig = Event()
        self.camera = XimeaCamera(self.frame_queue, self.finished_sig, self.control_queue)
        self.frame_dispatcher = FrameDispatcher(self.frame_queue, self.gui_frame_queue)

        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = display_gui.StimulusDisplayWindow(protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.win_main = QDialog()
        self.main_layout = QHBoxLayout()
        self.camera_view = camera_display.CameraViewWidget(self.gui_frame_queue,
                                                           self.control_queue,
                                                           camera_rotation=1)
        self.main_layout.addWidget(self.camera_view)

        self.win_control = control_gui.ProtocolControlWindow(app, protocol, self.win_stim_disp)
        self.win_control.update_ROI()
        self.main_layout.addWidget(self.win_control)

        self.win_main.setLayout(self.main_layout)
        self.win_main.show()

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()

        self.fish_data = metadata.MetadataFish()
        self.stimulus_data = dict(background=bg, motion=motion)
        metawidget = ParameterGui(self.fish_data)
        self.win_control.button_metadata.clicked.connect(metawidget.show)
        self.win_control.button_calibrate.clicked.connect(self.calibrate)

        self.camera.start()
        self.frame_dispatcher.start()

        app.exec_()

    def start_external(self):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5555")
        socket.send(b"start_recording")


    def calibrate(self):
        pass



    def consolidate_data(self):
        dc = metadata.DataCollector(fish_data)
        self.stimulus_data['window_shape'] = win_stim_disp.get_current_dims()
        dc.add_metadata('stimulation', 'window_shape',
                        win_stim_disp.get_current_dims())

        dc.save(self.folder)


if __name__=='__main__':
    exp = Experiment()
