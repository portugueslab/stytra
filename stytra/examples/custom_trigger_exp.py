# Here we see how to implement a simple new type of trigger that waits the
# number of files in a directory to change for triggering a simple protocol
# showing a Flash.

from pathlib import Path
from lightparam.param_qt import ParametrizedWidget, Param
from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.visual import Pause, FullFieldVisualStimulus
from stytra.triggering import Trigger
from PyQt5.QtWidgets import QFileDialog


# The simplest way to implement a new trigger is inheriting from the Trigger
# class and re-implement the check_trigger method with the desired condition. In
# our case, we'll ask to check for the number of files in a folder. The
# experiment will start only when a file is added or removed.


class NewFileTrigger(Trigger):
    def __init__(self, pathname):
        self.path = Path(pathname)
        self.files_n = len(list(self.path.glob("*")))
        super().__init__()

    def check_trigger(self):
        # When number of files changes, check_trigger will return True:
        n = len(list(self.path.glob("*")))
        if n != self.files_n:
            self.files_n = n
            return True
        else:
            return False


class FlashProtocol(Protocol):
    name = "flash protocol"

    def __init__(self):
        super().__init__()
        self.period_sec = Param(5.0)
        self.flash_duration = Param(2.0)

    def get_stim_sequence(self):
        stimuli = [
            Pause(duration=self.period_sec - self.flash_duration),
            FullFieldVisualStimulus(
                duration=self.flash_duration, color=(255, 255, 255)
            ),
        ]
        return stimuli


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    # Select a directory:
    app = QApplication([])
    folder = QFileDialog.getExistingDirectory(caption="Trigger folder", directory=None)

    # Instantiate the trigger:
    if folder is not None:
        trigger = NewFileTrigger(folder)

        # Call stytra assigning the triggering. Note that stytra will wait for
        # the trigger only if the "wait for trigger" checkbox is ticked!
        st = Stytra(app=app, protocol=FlashProtocol(), scope_triggering=trigger)
