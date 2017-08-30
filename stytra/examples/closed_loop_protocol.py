from stytra import TailTrackingExperiment, LightsheetExperiment
from stytra.stimulation.stimuli import ClosedLoop1D, GratingPainterStimulus
from stytra.calibration import CrossCalibrator
from stytra.stimulation.closed_loop import VigourMotionEstimator
from PyQt5.QtWidgets import QSplitter, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt
from stytra.stimulation.protocols import ReafferenceProtocol
from stytra.gui.plots import StreamingPlotWidget

import multiprocessing


class ClosedLoopExperiment(TailTrackingExperiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, calibrator=CrossCalibrator(fixed_length=160),
                         **kwargs)
        self.main_layout = QSplitter(Qt.Horizontal)
        self.behaviour_layout = QSplitter(Qt.Vertical)
        self.behaviour_layout.addWidget(self.camera_viewer)
        self.behaviour_layout.addWidget(self.stream_plot)

        self.main_layout.addWidget(self.behaviour_layout)
        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)
        self.set_protocol(ReafferenceProtocol(n_repeats=5, n_backwards=0,
            fish_motion_estimator=VigourMotionEstimator(
                                 self.data_acc_tailpoints, vigour_window=0.05),
            calibrator=self.calibrator))

        self.velocity_plot = StreamingPlotWidget(self.protocol.dynamic_log, data_acc_col=1,
                                                 xlink=self.stream_plot.streamplot)
        self.gui_refresh_timer.timeout.connect(self.velocity_plot.update)
        self.behaviour_layout.addWidget(self.velocity_plot)
        self.show()
        self.show_stimulus_screen()


if __name__ == '__main__':
    app = QApplication([])
    exp = ClosedLoopExperiment(app=app, name='closed_loop',
                              directory=r'D:\vilim/closed_loop/',
                              tracking_method='angle_sweep',
                              tracking_method_parameters={'n_segments': 9,
                                                          'filtering': True,
                                                          'color_invert': True})
    app.exec_()
