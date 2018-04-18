from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout,\
    QWidget, QComboBox, \
     QProgressBar

from pyqtgraph.parametertree import ParameterTree

import inspect

from stytra.stimulation import protocols
from stytra.stimulation.protocols import Protocol


class ProtocolDropdown(QComboBox):
    def __init__(self):
        super().__init__()
        self.setEditable(False)

        prot_classes = inspect.getmembers(protocols, inspect.isclass)
        self.prot_classdict = {prot[1].name: prot[1]
                               for prot in prot_classes if issubclass(prot[1],
                                                                      Protocol)}
        self.addItems(list(self.prot_classdict.keys()))


class ProtocolControlWidget(QWidget):
    """Widget for controlling the stimulation. Implement selection of the
    Protocol to be run, window for controlling protocol parameters,
    and progress bar to display progression of the protocol.
    """
    sig_closing = pyqtSignal()

    def __init__(self, experiment=None, *args):
        """
        :param experiment: Experiment object
        """
        super().__init__(*args)
        self.protocol_runner = experiment.protocol_runner

        self.experiment = experiment

        # Create parametertree for protocol parameter control
        self.protocol_params_tree = ParameterTree(showHeader=False)

        # Widgets for selecting the protocol:
        self.layout_prot_selection = QHBoxLayout()
        # Dropdown menu with the protocol classes found in the Experiment:
        self.combo_prot = QComboBox()
        self.combo_prot.addItems(list(self.experiment.prot_class_dict.keys()))
        # Window with the protocol parameters:
        self.protocol_params_butt = QPushButton('Protocol parameters')
        self.protocol_params_butt.clicked.connect(self.show_stim_params_gui)
        self.layout_prot_selection.addWidget(self.combo_prot)
        self.layout_prot_selection.addWidget(self.protocol_params_butt)

        # Widgets for protocol start and progression report:
        self.layout_run = QHBoxLayout()
        self.button_toggle_prot = QPushButton("▶")  # button for start/stop
        self.button_toggle_prot.clicked.connect(self.toggle_protocol_running)
        if self.protocol_runner.protocol is None:
            self.button_toggle_prot.setEnabled(False)
        self.progress_bar = QProgressBar()  # progress bar for the protocol
        self.progress_bar.setFormat('%p% %v/%m')
        self.layout_run.addWidget(self.button_toggle_prot)
        self.layout_run.addWidget(self.progress_bar)

        # Global layout:
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.layout_run)
        self.layout.addLayout(self.layout_prot_selection)
        self.setLayout(self.layout)

        # If last_protocol available, set as default:
        if self.experiment.last_protocol is not None:
            self.combo_prot.setCurrentIndex(
                list(self.experiment.prot_class_dict.keys()).index(
                    self.experiment.last_protocol))

        self.timer = None
        self.protocol_runner.sig_protocol_updated.connect(
            self.update_stim_duration)
        self.protocol_runner.sig_timestep.connect(self.update_progress)
        self.combo_prot.currentIndexChanged.connect(self.set_protocol)

        self.protocol_runner.sig_protocol_started.connect(self.toggle_icon)
        self.protocol_runner.sig_protocol_finished.connect(self.toggle_icon)

    def show_stim_params_gui(self):
        self.protocol_params_tree.setParameters(
            self.protocol_runner.protocol.params)
        self.protocol_params_tree.show()
        self.protocol_params_tree.setWindowTitle('Stimulus parameters')
        self.protocol_params_tree.resize(300, 600)

    def toggle_protocol_running(self):
        # Start/stop the protocol:
        if not self.protocol_runner.running:
            self.experiment.start_protocol()
            # self.button_toggle_prot.setText("■")
        else:
            self.experiment.end_protocol()
            # self.button_toggle_prot.setText("▶")
            self.toggle_icon()

    def toggle_icon(self):
        """ Change the play/stop icon of the GUI.
        """
        if self.button_toggle_prot.text() == "■":
            self.button_toggle_prot.setText("▶")
        else:
            self.button_toggle_prot.setText("■")

    def update_stim_duration(self):
        self.progress_bar.setMaximum(int(self.protocol_runner.duration))

    def update_progress(self):
        self.progress_bar.setValue(int(self.protocol_runner.t))

    def protocol_changed(self):
        self.progress_bar.setValue(0)

    def set_protocol(self): #, prot_name=None):
        """Use dropdown menu to change the protocol.
        """

        #if prot_name is None:
        self.protocol_runner.set_new_protocol(self.combo_prot.currentText())
        #else:
        #    self.protocol_runner.set_new_protocol(prot_name)
        self.button_toggle_prot.setEnabled(True)
        # self.protocol_params_tree.setParameters(self.protocol_runner.protocol.params)

    # def set_prot_from_dropdown(self):
    #     Protclass = self.experiment.prot_class_dict[
    #         self.combo_prot.currentText()]
    #     self.set_protocol(Protclass)


# class TrackingMethodDropdown(QComboBox):
#     def __init__(self):
#         super().__init__()
#         prot_classes = inspect.getmembers(protocols, inspect.isclass)
#
#         self.setEditable(False)
#         self.prot_classdict = {prot[1].name: prot[1]
#                                for prot in prot_classes if issubclass(prot[1],
#                                                                       Protocol)}
#
#         self.addItems(list(self.prot_classdict.keys()))

