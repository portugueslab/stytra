from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QProgressBar

import numpy as np
import pandas as pd
from stytra.stimulation.stimuli import Pause
from stytra.gui import display_gui, control_gui
import stytra.calibration as calibration
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import existing_file_background
from stytra.stimulation.stimuli import MovingSeamless
from stytra.gui.display_gui import StimulusDisplayWindow
from stytra.gui.control_gui import ProtocolControlWindow
from stytra.metadata import MetadataFish
from queue import Empty

import qdarkstyle


def make_spinning_protocol(n_vels=3, stim_duration=10, pause_duration=5,
                                 vel_mean=0.5, vel_std=0.3):
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


        # set up the stimuli

        refresh_rate = 1/60.

        motion = make_spinning_protocol()
        self.protocol_duration = motion.t.iat[-1]

        self.im_filename = r"C:\Users\vilim\experimental\underwater\66_underwater beach sand texture-seamless.jpg"
        bg = existing_file_background(self.im_filename)


        self.protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                                 duration=motion.t.iat[-1])],
                                                 dt=refresh_rate)

        self.calibrator = calibration.CircleCalibrator(dh=50)
        self.win_stim_disp = display_gui.StimulusDisplayWindow(self.protocol)
        self.win_stim_disp.widget_display.calibration = self.calibrator

        self.main_layout = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.main_layout)

        self.win_control = control_gui.ProtocolControlWindow(app, self.protocol, self.win_stim_disp)
        self.win_control.refresh_ROI()
        self.main_layout.addWidget(self.win_control)
        self.prog_bar = QProgressBar()
        # self.gui_timer.timeout.connect(self.update_progress)

        self.win_stim_disp.show()
        self.win_stim_disp.windowHandle().setScreen(app.screens()[1])
        self.win_stim_disp.showFullScreen()

        self.win_stim_disp.update_display_params()
        self.win_control.reset_ROI()

        self.show()

    # def update_progress(self):
    #     time_elapsed = datetime.datetime.now()-self.protocol.t_start
    #     self.prog_bar.setValue(int(time_elapsed*100/self.protocol_duration))


    def closeEvent(self, QCloseEvent):
        self.app.closeAllWindows()
        self.app.quit()


if __name__ == '__main__':
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    exp = Experiment(app)
    app.exec_()
