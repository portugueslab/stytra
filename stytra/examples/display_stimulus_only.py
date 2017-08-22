from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter, QProgressBar

import numpy as np
import pandas as pd
from stytra import Experiment
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import existing_file_background
from stytra.stimulation.stimuli import MovingSeamless


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


class StimulusOnyExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_layout = QSplitter(Qt.Horizontal)

        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)

        self.im_filename = r"J:\Vilim Stih\sync\underwater\40_water with stone and fish texture-seamless.jpg"
        bg = existing_file_background(self.im_filename)
        motion = make_spinning_protocol()
        self.protocol_duration = motion.t.iat[-1]

        print(self.protocol_duration)
        self.set_protocol(Protocol([MovingSeamless(background=bg, motion=motion,
                                                 duration=motion.t.iat[-1])]))

        self.show()
        self.show_stimulus_screen(full_screen=False)


if __name__ == '__main__':
    app = QApplication([])
    exp = StimulusOnyExperiment(app=app, name='stimulus_test',
                               directory=r'D:\vilim/')
    app.exec_()
