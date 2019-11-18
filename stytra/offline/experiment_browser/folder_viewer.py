import sys
import io
import os
from pathlib import Path
import json
import base64
from PIL import Image
import numpy as np

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from pyqtgraph.Qt import QtCore, QtGui

import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree


class DragDropLabel(QLabel):
    acceptedFormat = 'json'
    droppedFile = pyqtSignal(str)

    def __init__(self, parent):
        super(DragDropLabel, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.folder_path = url.toLocalFile()
            if os.path.isdir(self.folder_path):
                self.droppedFile.emit(self.folder_path)
            else:
                pass

class FolderViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Folder viewer'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)

        self.getbtn = QPushButton("Select folder")
        self.getbtn.clicked.connect(self.select_folder)

        self.draglbl = DragDropLabel(self)
        self.draglbl.setText("... or drop folder here".format(DragDropLabel.acceptedFormat.upper()))
        self.draglbl.setAlignment(QtCore.Qt.AlignCenter)
        self.draglbl.droppedFile.connect(self.list_folders)

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.getbtn, 0, 0, 1, 2)
        self.layout.addWidget(self.draglbl, 1, 0, 1, 2)

        self.setLayout(self.layout)
        self.show()

    def select_folder(self):
        dialog = QtGui.QFileDialog()
        self.folder_path = dialog.getExistingDirectory(None, "Select Folder")

        if not self.folder_path:
            pass
        else:
            self.list_folders(self.folder_path)

    def list_folders(self, path):
        self.data_directory = path
        self.fish_list = os.listdir(self.data_directory)
        self.list = QListWidget()
        self.list.addItems(self.fish_list)
        self.layout.addWidget(self.list, 2, 0)
        self.list.itemClicked.connect(self.do_smth)

    def do_smth(self, str):
        self.str = str
        self.fish_folder = Path(self.data_directory + '/{}/'.format(self.str.text()))
        print(list(self.fish_folder.glob('*.json')))





if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FolderViewer()
    sys.exit(app.exec_())