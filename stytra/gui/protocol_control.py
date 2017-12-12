from PyQt5.QtCore import QRectF, pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout,\
    QWidget, QLayout, QComboBox, \
     QProgressBar, QLabel, QSplitter

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
    sig_closing = pyqtSignal()

    def __init__(self, experiment=None, *args):
        """
        Widget for controlling the stimulation.
        :param app: Qt5 app
        :param experiment: Experiment object
        """
        super().__init__(*args)
        self.protocol_runner = experiment.protocol_runner

        self.experiment = experiment

        # Create parametertree for protocol parameter control
        self.protocol_params_tree = ParameterTree(showHeader=False)

        # Widgets for protocol choosing
        self.layout_choose = QHBoxLayout()
        # self.combo_prot = ProtocolDropdown()
        self.combo_prot = QComboBox()
        self.combo_prot.addItems(list(self.experiment.prot_class_dict.keys()))
        self.protocol_params_butt = QPushButton('Protocol parameters')
        self.protocol_params_butt.clicked.connect(self.show_stim_params_gui)
        self.layout_choose.addWidget(self.combo_prot)
        self.layout_choose.addWidget(self.protocol_params_butt)

        # Widgets for protocol running
        self.layout_run = QHBoxLayout()
        self.button_toggle_prot = QPushButton("▶")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat('%p% %v/%m')
        self.layout_run.addWidget(self.button_toggle_prot)
        self.layout_run.addWidget(self.progress_bar)

        self.button_toggle_prot.clicked.connect(self.toggle_protocol_running)
        if self.protocol_runner.protocol is None:
            self.button_toggle_prot.setEnabled(False)

        self.timer = None
        self.layout = QVBoxLayout()

        self.layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addLayout(self.layout_run)
        self.layout.addLayout(self.layout_choose)

        self.protocol_runner.sig_protocol_updated.connect(
            self.update_stim_duration)
        self.protocol_runner.sig_timestep.connect(self.update_progress)

        self.setLayout(self.layout)

        if self.experiment.last_protocol is not None:
            self.combo_prot.setCurrentIndex(
                list(self.experiment.prot_class_dict.keys()).index(
                self.experiment.last_protocol))
        self.combo_prot.currentIndexChanged.connect(self.set_prot_from_dropdown)

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
            self.button_toggle_prot.setText("■")
        else:
            self.experiment.end_protocol()
            self.button_toggle_prot.setText("▶")

    def update_stim_duration(self):
        self.progress_bar.setMaximum(int(self.protocol_runner.duration))

    def update_progress(self):
        self.progress_bar.setValue(int(self.protocol_runner.t))

    def protocol_changed(self):
        self.progress_bar.setValue(0)

    def set_protocol(self, Protclass):
        """Use dropdown menu to change the protocol.
        """
        protocol = Protclass()
        self.protocol_runner.set_new_protocol(protocol)
        self.button_toggle_prot.setEnabled(True)
        self.protocol_params_tree.setParameters(self.protocol_runner.protocol.params)

    def set_prot_from_dropdown(self):
        Protclass = self.experiment.prot_class_dict[
            self.combo_prot.currentText()]
        self.set_protocol(Protclass)


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

