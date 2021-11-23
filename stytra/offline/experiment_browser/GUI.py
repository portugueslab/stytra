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


class BrowserWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.metadata_viewer = JsonReader()
        self.exp_selector = FolderViewer(self.metadata_viewer)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.exp_selector)
        self.layout().addWidget(self.metadata_viewer)

        # self.exp_selector.list.itemClicked.connect(self.update_fish)

    def update_fish(self, str):
        self.str = str
        self.fish_folder = Path(self.data_directory + "/{}/".format(self.str.text()))
        # self.fish_metadata = list(self.fish_folder.glob('*.json'))


class DragDropLabel(QLabel):
    acceptedFormat = "json"
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


class JsonReader(QWidget):
    def __init__(self):
        super().__init__()
        self.title = "Json metadata reader"
        self.initUI()

    def initUI(self):
        self.layout = QGridLayout(self)

        self.setLayout(self.layout)
        self.show()

    #     self.setWindowTitle(self.title)
    #
    #     self.getbtn = QPushButton("Select file")
    #     self.getbtn.clicked.connect(self.get_file)
    #
    #     self.draglbl = DragDropLabel(self)
    #     self.draglbl.setText("... or drop .{} file here".format(DragDropLabel.acceptedFormat.upper()))
    #     self.draglbl.setAlignment(QtCore.Qt.AlignCenter)
    #     self.draglbl.droppedFile.connect(self.open_file)
    #
    #     self.layout = QGridLayout(self)
    #     self.layout.addWidget(self.getbtn, 0, 0, 1, 2)
    #     self.layout.addWidget(self.draglbl, 1, 0, 1, 2)
    #
    #     self.setLayout(self.layout)
    #     self.show()
    #
    # def get_file(self):
    #     self.path, _ = QFileDialog.getOpenFileName(filter="Json files (*.json)")
    #
    #     if not self.path:
    #         pass
    #     else:
    #         self.open_file(self.path)
    #
    # def open_file(self, filename):
    #     self.filename = filename
    #
    #     with open(filename) as json_file:
    #         self.metadata_dict = json.load(json_file)
    #
    #     self.display_tree_widget(self.metadata_dict)

    def display_tree_widget(self, fish):
        """Display the parameter tree from the experiment metadata.
        :param metadata: .json metadata
        """

        self.fish = fish
        print(self.fish)

        self.fish_folder = Path(self.data_directory + "/{}/".format(self.fish.text()))
        self.fish_metadata_path = list(self.fish_folder.glob("*.json"))

        with open(self.fish_metadata_path) as json_file:
            self.metadata = json.load(json_file)

        # Close previous tree widget
        self.close_tree()

        # Create a variable checking whether changes have been made to the parameter tree values
        self.has_changed = False

        # Create list with parameters for the tree
        self.parameters = self.create_parameters(self.fix_types(self.metadata))

        # Create tree of Parameter objects
        self.p = Parameter.create(name="params", type="group", children=self.parameters)

        # Save original state
        self.original_state = self.p.saveState()

        # Create ParameterTree widget
        self.tree = ParameterTree()
        self.tree.setParameters(self.p, showTop=False)
        self.tree.setWindowTitle("pyqtgraph example: Parameter Tree")

        # Display tree widget
        self.layout.addWidget(self.tree, 0, 0, 1, 2)

        # And buttons
        self.savebtn = QPushButton("Save changes")
        self.resetbtn = QPushButton("Reset changes")
        self.layout.addWidget(self.savebtn, 3, 0)
        self.layout.addWidget(self.resetbtn, 3, 1)
        self.savebtn.clicked.connect(self.save_treevals)
        self.resetbtn.clicked.connect(self.reset)

        # Send signal when any entry is changed
        self.p.sigTreeStateChanged.connect(self.change)

    def save_treevals(self):
        """Save current values of the parameter tree into a dictionary."""
        # Recover data from tree and store it in a dict
        self.treevals_dict = self.p.getValues()
        self.metadata_dict_mod = self.get_mod_dict(self.treevals_dict)

        # Nasty way to make new dict (with modified metadata) with same structure as the original one
        self.metadata_dict_mod["stimulus"]["log"] = self.metadata_dict["stimulus"][
            "log"
        ]
        self.metadata_dict_mod["stimulus"]["display_params"]["pos"] = json.loads(
            self.metadata_dict_mod["stimulus"]["display_params"]["pos"]
        )
        self.metadata_dict_mod["stimulus"]["display_params"]["size"] = json.loads(
            self.metadata_dict_mod["stimulus"]["display_params"]["size"]
        )

        self.show_warning()

    def show_warning(self):
        """Upon saving, display a warning message
        to choose whether to create a new metadata file or replace the existing one.
        """
        if self.has_changed:
            self.msg = QMessageBox()
            self.msg.setIcon(QMessageBox.Warning)
            self.setWindowTitle("Saving Warning")
            self.msg.setText("Some parameters have changed")
            self.msg.setInformativeText(
                "Do you want to overwrite the original .json metadata file?"
            )
            self.msg.addButton("Create new file", QMessageBox.AcceptRole)
            self.msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            self.ret = self.msg.exec_()

            if self.ret == QMessageBox.Yes:
                self.overwrite_metadata_file(self.metadata_dict_mod)
            elif self.ret == QMessageBox.AcceptRole:
                self.create_metadata_file(self.metadata_dict_mod)
            else:
                pass
        else:
            self.msg2 = QMessageBox()
            self.msg2.setIcon(QMessageBox.Information)
            self.setWindowTitle("Saving Warning")
            self.msg2.setText("No changes have been made.")
            self.msg2.addButton("OK", QMessageBox.AcceptRole)

            self.ret = self.msg2.exec_()

    def overwrite_metadata_file(self, metadata_dict_mod):
        # Overwritte original metadata file
        with open(self.filename, "w") as file:
            json.dump(metadata_dict_mod, file)

    def create_metadata_file(self, metadata_dict_mod):
        # Overwritte original metadata file
        self.name, self.ext = self.filename.split(".")
        with open("{}_modified.{}".format(self.name, self.ext), "w") as file:
            json.dump(metadata_dict_mod, file)

    def reset(self):
        """Reset parameter tree values to the original state after loading."""
        self.p.restoreState(self.original_state, recursive=True)
        # self.tree.setParameters(self.p, showTop=False)

    def fix_types(self, datadict):
        """Modify metadata dict so only accepted types are found."""
        param_dict = dict()
        for key, value in datadict.items():
            if isinstance(value, list):
                param_dict[key] = str(value)
            elif isinstance(value, dict):
                param_dict[key] = self.fix_types(value)
            else:
                param_dict[key] = value
        return param_dict

    def create_parameters(self, datadict):
        """Create list with parameters and Children to which the tree will be built from."""
        parameters = []
        for key, value in datadict.items():
            if key == "log":
                pass
            else:
                if isinstance(value, dict):
                    parameters.append(
                        {
                            "name": "{}".format(key),
                            "type": "group",
                            "children": self.create_parameters(value),
                        }
                    )
                else:
                    parameters.append(
                        {
                            "name": "{}".format(key),
                            "type": "{}".format(type(value).__name__),
                            "value": value,
                        }
                    )
        return parameters

    def get_mod_dict(self, treevals_dict):
        """Recursive function to convert into dict output of getValues function."""
        metadata_dict_mod = dict()
        for key, value in treevals_dict.items():
            if value[0] is None:
                metadata_dict_mod[key] = dict(self.get_mod_dict(value[1]))
            else:
                metadata_dict_mod[key] = value[0]

        return metadata_dict_mod

    def change(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.p.childPath(param)
            if path is not None:
                childName = ".".join(path)
            else:
                childName = param.name()
            print("  parameter: %s" % childName)
            print("  change:    %s" % change)
            print("  data:      %s" % str(data))
            print("  ----------")

            if change == "activated":
                pass
            else:
                self.has_changed = True

    def close_tree(self):
        try:
            self.layout.removeWidget(self.tree)
            self.tree.deleteLater()
            self.tree = None
        except AttributeError:
            pass


class FolderViewer(QWidget):
    def __init__(self, json_viewer):
        self.json_viewer = json_viewer
        super().__init__()
        self.title = "Folder viewer"
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)

        self.getbtn = QPushButton("Select folder")
        self.getbtn.clicked.connect(self.select_folder)

        self.draglbl = DragDropLabel(self)
        self.draglbl.setText(
            "... or drop folder here".format(DragDropLabel.acceptedFormat.upper())
        )
        self.draglbl.setAlignment(QtCore.Qt.AlignCenter)
        self.draglbl.droppedFile.connect(self.list_folders)

        self.jsontree = JsonReader()

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.getbtn, 0, 0, 1, 2)
        self.layout.addWidget(self.draglbl, 1, 0, 1, 2)

        # self.layout.setRowMinimumHeight(0, 50)
        # self.layout.setRowMinimumHeight(1, 50)
        self.setLayout(self.layout)
        self.show()

    def select_folder(self):
        dialog = QtGui.QFileDialog()
        self.folder_path = dialog.getExistingDirectory(None, "Select Folder")
        print(self.folder_path)

        # if not self.folder_path:
        #     pass
        # else:
        #     self.list_folders(self.folder_path)

    # def get_data_directory(self):

    def list_folders(self, path):
        self.data_directory = path
        self.fish_list = os.listdir(self.data_directory)
        self.list = QListWidget()
        self.list.addItems(self.fish_list)
        self.layout.addWidget(self.list, 2, 0)
        self.list.itemClicked.connect(self.json_viewer.display_tree_widget)

    # def do_smth(self, str):
    #     self.str = str
    #     self.fish_folder = Path(self.data_directory + '/{}/'.format(self.str.text()))
    #     self.fish_metadata = list(self.fish_folder.glob('*.json'))
    #
    #     with open(self.fish_metadata[0]) as json_file:
    #         self.metadata_dict = json.load(json_file)
    #
    #     self.jsontree.display_tree_widget(self.metadata_dict)
    #     # self.layout.addLayout(self.jsontree, 0, 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = BrowserWindow()
    ex.show()
    sys.exit(app.exec_())
