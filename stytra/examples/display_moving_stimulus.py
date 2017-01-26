from PyQt5.QtWidgets import QApplication
import qdarkstyle
from stytra.stimulation.stimuli import MovingSeamless, Flash
from stytra.stimulation import Protocol
from stytra.stimulation.backgrounds import noise_background
import pandas as pd
import numpy as np
import deepdish.io as dio
from stytra.gui import control_gui, display_gui
from functools import partial
import stytra.calibration as calibration

if __name__ == '__main__':

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

    bg = noise_background((1000, 1000), 10)

    motion = pd.DataFrame(dict(t=t_break, x=xs, y=ys))
    protocol = Protocol([MovingSeamless(background=bg, motion=motion,
                                        duration=n_vels*stim_duration)],
                        dt=refresh_rate)

    win_stim_disp = display_gui.StimulusDisplayWindow(protocol)
    win_stim_disp.widget_display.calibration = partial(calibration.paint_circles,
                                        dh=100, r=5)

    win_control = control_gui.ProtocolControlWindow(app, protocol, win_stim_disp)
    win_control.show()
    win_control.update_ROI()
    win_stim_disp.show()
    win_stim_disp.windowHandle().setScreen(app.screens()[1])
    win_stim_disp.showFullScreen()

    dio.save('test_stim.h5', dict(motion=motion,
              window_params=win_stim_disp.get_current_dims(),
              background=bg))
    app.exec_()