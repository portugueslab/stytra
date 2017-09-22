from stytra import TailTrackingExperiment, LightsheetExperiment
from stytra.stimulation.stimuli import ClosedLoop1D, GratingPainterStimulus
from stytra.calibration import CrossCalibrator
from stytra.stimulation.closed_loop import VigourMotionEstimator
from PyQt5.QtWidgets import QSplitter, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt
from stytra.stimulation.protocols import ReafferenceProtocol
from stytra.gui.plots import StreamingPlotWidget

import argparse


class ClosedLoopExperiment(TailTrackingExperiment, LightsheetExperiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, calibrator=CrossCalibrator(fixed_length=160),
                         **kwargs)
        self.metadata_general.experiment_name = 'reafference'
        self.main_layout = QSplitter(Qt.Horizontal)
        self.behaviour_layout = QSplitter(Qt.Vertical)
        self.behaviour_layout.addWidget(self.camera_viewer)
        self.behaviour_layout.addWidget(self.tail_stream_plot)

        self.main_layout.addWidget(self.behaviour_layout)
        self.main_layout.addWidget(self.widget_control)
        self.setCentralWidget(self.main_layout)
        self.set_protocol(ReafferenceProtocol(n_repeats=20, n_backwards=7, forward_duration=5, pause_duration=5,
            fish_motion_estimator=VigourMotionEstimator(
                                 self.data_acc_tailpoints, vigour_window=0.05),
            calibrator=self.calibrator, base_gain=40))

        self.velocity_plot = StreamingPlotWidget(self.protocol.dynamic_log, data_acc_var='vel',
                                                 xlink=self.tail_stream_plot.streamplot, y_range=(-25, 15))
        self.fish_velocity_plot = StreamingPlotWidget(self.protocol.dynamic_log, data_acc_var='fish_velocity',
                                                      xlink=self.tail_stream_plot.streamplot, y_range=(0, 5))

        self.gui_refresh_timer.timeout.connect(self.velocity_plot.update)
        self.gui_refresh_timer.timeout.connect(self.fish_velocity_plot.update)
        self.behaviour_layout.addWidget(self.velocity_plot)
        self.behaviour_layout.addWidget(self.fish_velocity_plot)
        self.show()
        self.show_stimulus_screen()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tail-invert',
                        action='store_true')
    parser.add_argument('--debug',
                        action='store_true')
    args = parser.parse_args()
    print(args)
    app = QApplication([])
    exp = ClosedLoopExperiment(app=app, name='closed_loop',
                              directory=r'D:\vilim/closed_loop/',
                              tracking_method='angle_sweep',
                              tracking_method_parameters={'n_segments': 9,
                                                          'filtering': True,
                                                          'color_invert': args.tail_invert},
                               debug_mode=args.debug)
    app.exec_()
