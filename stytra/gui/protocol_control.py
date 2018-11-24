from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDockWidget,
    QProgressBar,
    QToolBar,
    QLabel,
)
from stytra.stimulation import ProtocolRunner
import datetime

from lightparam.gui import ParameterGui
from math import floor, ceil


class ProtocolControlToolbar(QToolBar):
    """GUI for controlling a ProtocolRunner.

    This class implements:

        - selection box of the Protocol to be run;
        - window for controlling Protocol parameters;
        - toggle button for starting/stopping the Protocol;
        - progress bar to display progression of the Protocol.

     Parameters
    ----------
    protocol_runner: :class:`ProtocolRunner <stytra.stimulation.ProtocolRunner>` object
        ProtocolRunner that is controlled by the GUI.

    **Signals**
    """

    sig_start_protocol = pyqtSignal()
    """ Emitted via the toggle button click, meant to
                         start the protocol."""
    sig_stop_protocol = pyqtSignal()
    """ Emitted via the toggle button click, meant to
                         abort the protocol."""

    def __init__(self, protocol_runner: ProtocolRunner, main_window=None):
        """ """
        super().__init__("Protocol running")
        self.main_window = main_window
        self.protocol_runner = protocol_runner

        # Label with the protocol classes found in the Experiment:
        self.label_prot = QLabel(text=self.protocol_runner.protocol.name.split("/")[-1])
        self.addWidget(self.label_prot)

        # Window with the protocol parameters:
        self.act_edit = self.addAction("Edit protocol parameters")
        self.act_edit.triggered.connect(self.show_stim_params_gui)

        self.toggleStatus = self.addAction("▶")
        self.toggleStatus.triggered.connect(self.toggle_protocol_running)

        # Progress bar for monitoring the protocol:
        self.progress_bar = QProgressBar()
        self.addSeparator()
        self.addWidget(self.progress_bar)

        # Connect events and signals from the ProtocolRunner to update the GUI:
        self.update_progress()
        self.protocol_runner.sig_timestep.connect(self.update_progress)

        self.protocol_runner.sig_protocol_started.connect(self.toggle_icon)
        self.protocol_runner.sig_protocol_finished.connect(self.toggle_icon)

    def show_stim_params_gui(self):
        """Create and show window to update protocol parameters.
        """
        self.prot_param_win = QDockWidget("Protocol parameters", self.main_window)
        self.prot_param_win.setWidget(ParameterGui(self.protocol_runner.protocol))
        self.main_window.docks.append(self.prot_param_win)
        self.main_window.addDockWidget(Qt.RightDockWidgetArea, self.prot_param_win)

    def toggle_protocol_running(self):
        """Emit the start and stop signals. These can be used in the Experiment
        class or directly connected with the respective ProtocolRunner
        start() and stop() methods.

        Parameters
        ----------

        Returns
        -------

        """
        # Start/stop the protocol:
        if not self.protocol_runner.running:
            self.sig_start_protocol.emit()
        else:
            self.sig_stop_protocol.emit()
            self.toggle_icon()

    def toggle_icon(self):
        """Change the play/stop icon of the GUI.
        """
        if self.toggleStatus.text() == "■":
            self.toggleStatus.setText("▶")
            self.progress_bar.setValue(0)
        else:
            self.toggleStatus.setText("■")

    def update_progress(self):
        """ Update progress bar
        """
        self.progress_bar.setMaximum(int(self.protocol_runner.duration))
        self.progress_bar.setValue(int(self.protocol_runner.t))

        rem = ceil(self.protocol_runner.duration - self.protocol_runner.t)
        rem_min = int(floor(rem / 60))
        time_info = "{}/{}s ({}:{} remaining)".format(
            int(self.protocol_runner.t),
            int(self.protocol_runner.duration),
            rem_min,
            int(rem - rem_min * 60),
        )

        # If experiment started, add expected end time:
        if self.protocol_runner.t_start is not None:
            exp_end_time = self.protocol_runner.t_start + datetime.timedelta(
                seconds=self.protocol_runner.duration
            )
            time_info += " - Ending at {}:{}:{}".format(
                exp_end_time.hour, exp_end_time.minute, exp_end_time.second
            )

        self.progress_bar.setFormat(time_info)
