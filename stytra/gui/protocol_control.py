from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QComboBox,
    QProgressBar,
)

from pyqtgraph.parametertree import ParameterTree
from poparam.gui import ParameterGui


class ProtocolControlWidget(QWidget):
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

    def __init__(self, protocol_runner=None, *args):
        """ """
        super().__init__(*args)
        self.protocol_runner = protocol_runner

        # Create parametertree for protocol parameter control
        self.protocol_params_tree = ParameterTree(showHeader=False)

        # Layout for selecting the protocol:
        self.lyt_prot_selection = QHBoxLayout()

        # Dropdown menu with the protocol classes found in the Experiment:
        self.combo_prot = QComboBox()
        self.combo_prot.addItems(list(self.protocol_runner.prot_class_dict.keys()))

        self.combo_prot.currentIndexChanged.connect(self.set_protocol)
        self.lyt_prot_selection.addWidget(self.combo_prot)

        # Window with the protocol parameters:
        self.protocol_params_butt = QPushButton("Protocol parameters")
        self.protocol_params_butt.clicked.connect(self.show_stim_params_gui)
        self.lyt_prot_selection.addWidget(self.protocol_params_butt)

        # Layout for protocol start and progression report:
        self.lyt_run = QHBoxLayout()

        # Button for startup:
        self.button_toggle_prot = QPushButton("▶")

        self.button_toggle_prot.clicked.connect(self.toggle_protocol_running)
        self.lyt_run.addWidget(self.button_toggle_prot)

        # Progress bar for monitoring the protocol:
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p% %v/%m")

        self.lyt_run.addWidget(self.progress_bar)

        # Global layout:
        self.lyt = QVBoxLayout()
        self.lyt.setContentsMargins(0, 0, 0, 0)
        self.lyt.addLayout(self.lyt_run)
        self.lyt.addLayout(self.lyt_prot_selection)
        self.setLayout(self.lyt)

        self.timer = None

        # Connect events and signals from the ProtocolRunner to update the GUI:
        print('connecting')
        self.protocol_runner.sig_protocol_updated.connect(self.update_stim_duration)
        # self.update_stim_duration()
        self.protocol_runner.sig_timestep.connect(self.update_progress)

        self.protocol_runner.sig_protocol_started.connect(self.toggle_icon)
        self.protocol_runner.sig_protocol_finished.connect(self.toggle_icon)

        # If a previous protocol was already set in the protocol runner
        # change the GUI values accordingly:
        if protocol_runner.protocol is not None:
            self.combo_prot.setCurrentText(protocol_runner.protocol.name)
        else:
            self.set_protocol()

    def show_stim_params_gui(self):
        """Create and show window to update protocol parameters.
        """
        self.prot_param_win = QWidget()
        self.prot_param_win.setLayout(QHBoxLayout())
        self.prot_param_win.layout().addWidget(
            ParameterGui(self.protocol_runner.protocol))
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
            self.sig_start_protocol.emit()
        else:
            self.sig_stop_protocol.emit()
            self.toggle_icon()

    def toggle_icon(self):
        """Change the play/stop icon of the GUI.
        """
        if self.button_toggle_prot.text() == "■":
            self.button_toggle_prot.setText("▶")
            self.progress_bar.setValue(0)
        else:
            self.button_toggle_prot.setText("■")

    def update_stim_duration(self):
        """ Change the displayed durtion of the stimulus
        """
        print('updating duration')
        self.progress_bar.setMaximum(int(self.protocol_runner.duration))
        self.progress_bar.setValue(0)

    def update_progress(self):
        """ Update progress bar
        """
        self.progress_bar.setValue(int(self.protocol_runner.t))

    def set_protocol(self):
        """Use value in the dropdown menu to change the protocol.
        """
        protocol_name = self.combo_prot.currentText()
        self.protocol_runner.set_new_protocol(protocol_name)
        self.button_toggle_prot.setEnabled(True)
