from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget, QSplitter
import qdarkstyle
from stytra.stimulation.stimuli import MovingSeamless
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import noise_background, poisson_disk_background, existing_file_background
import pandas as pd
import numpy as np
from stytra.gui import control_gui, display_gui, camera_display
import stytra.calibration as calibration


class Experiment(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app


        # set up the stimuli
        n_vels = 120
        stim_duration = 15
        refresh_rate = 1/60.

        t_break = np.arange(n_vels+1)*stim_duration

        xs = np.zeros(n_vels+1)
        ys = np.zeros(n_vels+1)
        vel_mean = 30
        vel_std = 5
        angles = np.random.uniform(0, 2*np.pi, n_vels)# np.array([0, np.pi/2, np.pi, 3*np.pi/2]) #np.random.uniform(0, 2*np.pi, n_vels)
        vels = np.random.randn(n_vels)*vel_std+vel_mean #np.array([50]*n_vels) #

        for i in range(n_vels):
            xs[i+1] = xs[i] + stim_duration * vels[i]*np.cos(angles[i])
            ys[i + 1] = ys[i] + stim_duration * vels[i]*np.sin(angles[i])

        bg = existing_file_background(r"C:\Users\vilim\experimental\poisson_inverted.h5")

        motion = pd.DataFrame(dict(t=t_break, x=xs, y=ys))
        self.protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                                 duration=n_vels*stim_duration)],
                                                 dt=refresh_rate)

        # queues for interprocess communication
        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = display_gui.StimulusDisplayWindow(self.protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.main_layout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_layout)

        self.win_control = control_gui.ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.win_control.refresh_ROI()
        self.main_layout.addWidget(self.win_control)

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()

        print(self.win_stim_disp.display_params)
        self.win_stim_disp.update_display_params()
        self.win_control.reset_ROI()

        self.show()


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
