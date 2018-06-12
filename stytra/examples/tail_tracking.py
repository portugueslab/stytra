from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSplitter

from stytra import TailTrackingExperiment


class TailTrackImplementation(TailTrackingExperiment):
    """ """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_layout = QSplitter(Qt.Vertical)
        self.main_layout.addWidget(self.camera_viewer)
        self.main_layout.addWidget(self.tail_stream_plot)

        self.setCentralWidget(self.main_layout)
        self.show()


if __name__ == '__main__':
    app = QApplication([])
    exp = TailTrackImplementation(app=app, name='tail_tracking', directory=r'C:\Users\lpetrucco\Desktop',
                                  tracking_method='angle_sweep',
                                  tracking_method_parameters={'num_points': 9,
                                                              'filtering': True,
                                                              'color_invert': False})
    app.exec_()
