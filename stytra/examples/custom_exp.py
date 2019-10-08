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
        return [Stimulus(duration=5.0)]


# Little demonstration on how to use a custom experiment to bypass standard
# launching through Stytra class. This little experiment simply add an additional
# message box warning the user to confirm before running the protocol.


class CustomExperiment(Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start = False

    def start_protocol(self):
        self.start = False
        # Show message box with PyQt:
        msgBox = QMessageBox()
        msgBox.setText("Start the protocol when ready!")
        msgBox.setStandardButtons(QMessageBox.Ok)
        _ = msgBox.exec_()
        super().start_protocol()  # call the super() start_protocol method


if __name__ == "__main__":
    # Here we do not use the Stytra constructor but we instantiate an experiment
    # and we start it in the script. Even though this is an internal Experiment
    # subtype, a user can define a new Experiment subclass and start it
    # this way.
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    protocol = FlashProtocol()
    exp = CustomExperiment(protocol=protocol, app=app)
    exp.start_experiment()
    app.exec_()
