from stytra.experiments import Experiment
from stytra.stimulation import Protocol
import qdarkstyle
from PyQt5.QtWidgets import QApplication
from stytra.stimulation.stimuli import Stimulus
from PyQt5.QtWidgets import QMessageBox


# Here ve define an empty protocol:
class FlashProtocol(Protocol):
    name = "empty_protocol"  # every protocol must have a name.

    def get_stim_sequence(self):
        return [Stimulus(duration=5.),]


class CustomExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start = False

    def start_protocol(self):
        self.start = False

        msgBox = QMessageBox()
        msgBox.setText('Start the protocol when ready')
        msgBox.setStandardButtons(QMessageBox.Ok)
        ret = msgBox.exec_()
        super().start_protocol()



if __name__ == "__main__":
    # Here we do not use the Stytra constructor but we instantiate an experiment
    # and we start it in the script. Even though this is an internal Experiment
    # subtype, a user can define a new Experiment subclass and start it
    # this way.
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    protocol = FlashProtocol()
    exp = CustomExperiment(protocol=protocol,
                     app=app)
    exp.start_experiment()
    app.exec_()
