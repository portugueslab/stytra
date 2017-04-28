from PyQt5.QtWidgets import QApplication
from stytra.gui.control_gui import ProtocolControlWindow
import qdarkstyle



class Experiment:
    def __init__(self, directory, name):
        self.app = QApplication([])
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        self.directory = directory
        self.name = name

        self.data_sources = []


    #def add_data_source:


    #def save(self):



