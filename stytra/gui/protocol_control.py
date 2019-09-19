from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtWidgets import QProgressBar, QToolBar
from stytra.stimulation import ProtocolRunner
import datetime

from lightparam.gui import ParameterGui
from math import floor, ceil

from stytra.gui.buttons import IconButton, ToggleIconButton


class ProtocolControlToolbar(QToolBar):
    """GUI for controlling a ProtocolRunner.

    This class implements the toolbar for controlling the protocol:

        - toggle button for starting/stopping the Protocol;
        - progress bar to display progression of the Protocol.
        - a button and  window for controlling Protocol parameters;

    Parameters
    ----------
    protocol_runner: :class:`ProtocolRunner <stytra.stimulation.ProtocolRunner>` object
        ProtocolRunner that is controlled by the GUI.



    Signals:
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
        self.setIconSize(QSize(32, 32))
        self.main_window = main_window
        self.protocol_runner = protocol_runner

        self.update_duration_each = 120
        self._update_duration_i = 0

        self.toggleStatus = ToggleIconButton(
            icon_off="play", icon_on="stop", action_on="play", on=False
        )
        self.toggleStatus.clicked.connect(self.toggle_protocol_running)
        self.addWidget(self.toggleStatus)

        # Progress bar for monitoring the protocol:
        self.progress_bar = QProgressBar()
        self.addSeparator()
        self.addWidget(self.progress_bar)

        # Window with the protocol parameters:
        self.act_edit = IconButton(
            action_name="Edit protocol parameters", icon_name="edit_protocol"
        )
        self.act_edit.clicked.connect(self.show_stim_params_gui)
        self.addWidget(self.act_edit)

        # Connect events and signals from the ProtocolRunner to update the GUI:
        self.update_progress()
        self.protocol_runner.sig_timestep.connect(self.update_progress)

        self.protocol_runner.sig_protocol_finished.connect(self.toggle_icon)
        self.protocol_runner.sig_protocol_updated.connect(self.update_progress)
        self.protocol_runner.sig_protocol_interrupted.connect(self.toggle_icon)

    def show_stim_params_gui(self):
        """Create and show window to update protocol parameters.
        """
        self.prot_param_win = ParameterGui(self.protocol_runner.protocol)
        self.prot_param_win.show()

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
            self.progress_bar.setValue(0)
            self.sig_start_protocol.emit()
        else:
            self.sig_stop_protocol.emit()

    def toggle_icon(self):
        self.toggleStatus.flip_icon(self.protocol_runner.running)
        self.update_progress()

    def update_progress(self):
        """ Update progress bar
        """

        # if self._update_duration_i == 0:
        #   pass
        # self.protocol_runner.duration = self.protocol_runner.get_duration()
        self._update_duration_i = (
            self._update_duration_i + 1
        ) % self.update_duration_each

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
        if self.protocol_runner.running:
            exp_end_time = self.protocol_runner.experiment.t0 + datetime.timedelta(
                seconds=self.protocol_runner.duration
            )
            time_info += " - Ending at {}:{}:{}".format(
                exp_end_time.hour, exp_end_time.minute, exp_end_time.second
            )

        self.progress_bar.setFormat(time_info)
