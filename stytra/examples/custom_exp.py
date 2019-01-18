from stytra.stimulation.stimuli import VisualStimulus
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QBrush, QColor
from pathlib import Path


from stytra.experiments.tracking_experiments import TrackingExperiment
from stytra.stimulation import Protocol
import qdarkstyle
from PyQt5.QtWidgets import QApplication


class NewStimulus(VisualStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = (255, 255, 255)

    def paint(self, p, w, h):
        p.setBrush(QBrush(QColor(*self.color)))  # Use chosen color
        p.drawRect(QRect(0, 0, w, h))  # draw full field rectangle

    def update(self):
        fish_vel = self._experiment.estimator.get_velocity()
        # change color if speed of the fish is higher than threshold:
        if fish_vel < -5:
            self.color = (255, 0, 0)
        else:
            self.color = (255, 255, 255)


class CustomProtocol(Protocol):
    name = "custom protocol"  # protocol name

    stytra_config = dict(
        tracking=dict(method="tail", estimator="vigor"),
        camera=dict(
            video_file=str(Path(__file__).parent / "assets" / "fish_compressed.h5")
        ),
    )

    def get_stim_sequence(self):
        return [NewStimulus(duration=10)]


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    protocol = CustomProtocol()
    exp = TrackingExperiment(protocol=protocol,
                             app=app,
                             **protocol.stytra_config)
    exp.start_experiment()
    app.exec_()
