"""
    Author: Ot Prat
"""

import sys
import io
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
    """ Empty label on which you can drag a file to open it.
    """

    acceptedFormat = "json"
    droppedFile = pyqtSignal(str)

    def __init__(self, parent):
        super(DragDropLabel, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """

        Parameters
        ----------
        event :
            

        Returns
        -------

        """
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """

        Parameters
        ----------
        event :
            

        Returns
        -------

        """
        for url in event.mimeData().urls():
            self.filename = url.toLocalFile()
            if list(self.filename.split("."))[-1] == self.acceptedFormat:
                self.droppedFile.emit(self.filename)
            else:
                pass


class JsonReader(QWidget):
    """ """

    def __init__(self):
        super().__init__()
        self.title = "Json metadata reader"
        self.left = 100
        self.top = 100
        self.width = 500
        self.height = 500
        self.initUI()

    def initUI(self):
        """ """
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.getbtn = QPushButton("Select file")
        self.getbtn.clicked.connect(self.get_file)

        self.draglbl = DragDropLabel(self)
        self.draglbl.setText(
            "... or drop .{} file here".format(DragDropLabel.acceptedFormat.upper())
        )
        self.draglbl.setAlignment(QtCore.Qt.AlignCenter)
        self.draglbl.droppedFile.connect(self.open_file)

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.getbtn, 0, 0)
        self.layout.addWidget(self.draglbl, 1, 0)
        self.layout.setColumnMinimumWidth(0, 500)

        self.setLayout(self.layout)
        self.show()

    def get_file(self):
        """ """
        self.path, _ = QFileDialog.getOpenFileName(filter="Json files (*.json)")

        if not self.path:
            pass
        else:
            self.open_file(self.path)

    def open_file(self, filename):
        """

        Parameters
        ----------
        filename :
            

        Returns
        -------

        """
        self.filename = filename

        with open(filename) as json_file:
            self.metadata_dict = json.load(json_file)

        self.display_tree_widget(self.metadata_dict)

    def display_tree_widget(self, metadata):
        """Display the parameter tree from the experiment metadata.

        Parameters
        ----------
        metadata :
            json metadata

        Returns
        -------

        """
        # Close previous tree widget
        self.close_tree()

        # Create a variable checking whether changes have been made to the parameter tree values
        self.has_changed = False

        # Create list with parameters for the tree
        self.parameters = self.create_parameters(self.fix_types(metadata))

        # Add parameters for Save buttons and Image options
        self.parameters.append(
            {
                "name": "Metadata Image Options",
                "type": "group",
                "children": [
                    {"name": "Append Image", "type": "action"},
                    {"name": "View Image", "type": "action"},
                ],
            }
        )

        self.parameters.append(
            {
                "name": "Save/Reset metadata",
                "type": "group",
                "children": [
                    {"name": "Save changes", "type": "action"},
                    {"name": "Reset changes", "type": "action"},
                ],
            }
        )

        # Create tree of Parameter objects
        self.p = Parameter.create(name="params", type="group", children=self.parameters)

        # Check if Image parameters already exist. If they don't,
        # add them and update Parameter object
        self.children_list = []
        for child in self.p.children():
            self.children_list.append(str(child).split("'")[1])

        # Save original state
        self.original_state = self.p.saveState()

        # Connect Save/Reset buttons to respective functions
        self.p.param("Save/Reset metadata", "Save changes").sigActivated.connect(
            self.save_treevals
        )
        self.p.param("Save/Reset metadata", "Reset changes").sigActivated.connect(
            self.reset
        )

        # Create ParameterTree widget
        self.tree = ParameterTree()
        self.tree.setParameters(self.p, showTop=False)
        self.tree.setWindowTitle("pyqtgraph example: Parameter Tree")

        # Display tree widget
        self.layout.addWidget(self.tree, 2, 0)

        # Send signal when any entry is changed
        self.p.sigTreeStateChanged.connect(self.change)

    def append_img(self):
        """Attach a .png image to the metadata file."""
        self.imagefile, _ = QFileDialog.getOpenFileName(filter="png images (*.png)")

        if not self.imagefile:
            pass
        else:
            with open(self.imagefile, "rb") as f:
                self.img = f.read()
            self.encoded_img = base64.b64encode(self.img)
            self.encoded_img = self.encoded_img.decode("utf8")
            self.p.param("Metadata Image").setValue(self.encoded_img)
            self.p.param("Metadata Image").setDefault(self.encoded_img)

    def display_img(self):
        """Show image appended to the metadata file"""
        try:
            self.layout.removeWidget(self.imglbl)
            self.imglbl.deleteLater()
            self.imglbl = None
        except AttributeError:
            pass

        if not self.p.param("Metadata Image").defaultValue():
            self.imglbl = QLabel("No image associated to this metadata")
            self.layout.addWidget(self.imglbl, 2, 1)

            try:
                self.layout.removeWidget(self.viewbtn)
                self.viewbtn.deleteLater()
                self.viewbtn = None
            except AttributeError:
                pass

        else:
            self.figstring = self.p.param("Metadata Image").defaultValue()
            self.figbytes = self.figstring.encode("utf8")
            self.figbytes = base64.b64decode(self.figbytes)

            self.viewbtn = QPushButton("Zoom image")
            self.viewbtn.clicked.connect(self.image_viewer)

            self.image = QtGui.QPixmap()
            self.image.loadFromData(self.figbytes)
            self.image = self.image.scaledToHeight(500)

            self.imglbl = QLabel()
            self.imglbl.setPixmap(self.image)
            self.layout.addWidget(self.imglbl, 0, 1, 3, 1)
            self.layout.addWidget(self.viewbtn, 3, 1)

    def image_viewer(self):
        """Open metadata image in the Image Viewer from PyQtGraph."""
        self.win = QtGui.QMainWindow()
        self.win.resize(800, 800)

        self.fignp = np.array(Image.open(io.BytesIO(self.figbytes)))
        self.fignp = np.swapaxes(self.fignp, 0, 1)
        self.imv = pg.ImageView()
        self.imv.setImage(self.fignp)

        self.win.setCentralWidget(self.imv)
        self.win.setWindowTitle("Metadata Image")
        self.win.show()

    def save_treevals(self):
        """Save current values of the parameter tree into a dictionary."""
        # Recover data from tree and store it in a dict
        self.treevals_dict = self.p.getValues()
        self.metadata_dict_mod = self.get_mod_dict(self.treevals_dict)

        # Nasty way to make new dict (with modified metadata) with same structure as the original one
        self.metadata_dict_mod.pop("Save/Reset metadata")
        self.metadata_dict_mod.pop("Metadata Image Options")
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

        Parameters
        ----------

        Returns
        -------

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
        """

        Parameters
        ----------
        metadata_dict_mod :
            

        Returns
        -------

        """
        # Overwritte original metadata file
        with open(self.filename, "w") as file:
            json.dump(metadata_dict_mod, file)

    def create_metadata_file(self, metadata_dict_mod):
        """

        Parameters
        ----------
        metadata_dict_mod :
            

        Returns
        -------

        """
        # Overwritte original metadata file
        self.name, self.ext = self.filename.split(".")
        with open("{}_modified.{}".format(self.name, self.ext), "w") as file:
            json.dump(metadata_dict_mod, file)

    def reset(self):
        """Reset parameter tree values to the original state after loading."""
        self.p.restoreState(self.original_state, recursive=True)
        self.tree.setParameters(self.p, showTop=False)

    def fix_types(self, datadict):
        """Modify metadata dict so only accepted types are found.

        Parameters
        ----------
        datadict :
            

        Returns
        -------

        """
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
        """Create list with parameters and Children to which the tree will be built from.

        Parameters
        ----------
        datadict :
            

        Returns
        -------

        """
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
        """Recursive function to convert into dict output of getValues function.

        Parameters
        ----------
        treevals_dict :
            

        Returns
        -------

        """
        metadata_dict_mod = dict()
        for key, value in treevals_dict.items():
            if value[0] is None:
                metadata_dict_mod[key] = dict(self.get_mod_dict(value[1]))
            else:
                metadata_dict_mod[key] = value[0]

        return metadata_dict_mod

    def change(self, param, changes):
        """

        Parameters
        ----------
        param :
            
        changes :
            

        Returns
        -------

        """
        for param, change, data in changes:
            path = self.p.childPath(param)
            if path is not None:
                childName = ".".join(path)
            else:
                childName = param.name()

            if change == "activated":
                pass
            else:
                self.has_changed = True

    def close_tree(self):
        """ """
        try:
            self.layout.removeWidget(self.tree)
            self.tree.deleteLater()
            self.tree = None
        except AttributeError:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = JsonReader()
    sys.exit(app.exec_())
