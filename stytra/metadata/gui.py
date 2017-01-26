from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QDialog, \
    QLabel, QLineEdit, QPushButton, QComboBox
from PyQt5.QtGui import QIntValidator, QDoubleValidator
import param
from param.parameterized import classlist


def wtype(pobj):
    # map of param types over control classes:
    param_map_to_widget = {
        param.String: StringControl,
        param.Number: NumericControl,
        param.Integer: IntegerControl,
        param.ObjectSelector:  ListControl
    }

    for t in classlist(type(pobj))[::-1]:
        if t in param_map_to_widget:
            return param_map_to_widget[t]


class MetadataGui(QWidget):
    """
    Widget for displaying metadata controls.
    """

    def __init__(self, parameterized=None,  *args, **kwargs):
        """ Constructor

        :param parameterized: object parameterized with param module
        """

        super().__init__(*args, **kwargs)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.parameter_controls = []
        self.parameterized = parameterized

        # Add controls for all the parameters:
        for param_name in self.parameterized.params().keys():
            if not param_name == 'name':
                self.add_parameter_to_gui(param_name)

        # Connect ok button for saving data:
        ok_butt = QPushButton("Save Metadata")
        ok_butt.clicked.connect(self.save_meta)
        self.layout.addWidget(ok_butt)

    def add_parameter_to_gui(self, param_name):
        print(param_name)
        """ Add a new control to the widget.
        :param param_name: name of the parameter to add (string)
        """
        param_obj = self.parameterized.params(param_name)
        widget_class = wtype(param_obj)
        print(widget_class)
        new_control = widget_class(self.parameterized.params(param_name), param_name)

        self.parameter_controls.append(new_control)
        self.layout.addWidget(new_control)

    def save_meta(self):
        """ Parse metadata from the GUI
        """
        for parameter_control in self.parameter_controls:
            try:
                setattr(self.parameterized, parameter_control.name, parameter_control.get_value())
            except ValueError:
                # TODO give some warning to the user that they set it incorrectly
                parameter_control.setStyleSheet('background-color:(240, 120,100);')


class ParameterControl(QWidget):
    """
    Class for the single parameters controls of the metadata GUI
    """
    def __init__(self, parameter, name, *args, **kwargs):
        """ Constructor
        :param parameter: parameter for the new control (Parameter object)
        :param name: name of the parameter (string)
        """
        super().__init__(*args, **kwargs)
        assert isinstance(parameter, param.Parameter)  # Check input
        self.name = name
        self.label = self._pretty_print(name)
        self.parameter = parameter

        # Create layout and add label to the control:
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel(self.label))

        # Create control widget according to parameter type:
        self.control_widget = self.create_control_widget()
        self.layout.addWidget(self.control_widget)

    def _pretty_print(self, s):
        n = s.replace("_", " ")
        n = n.capitalize()
        return n

    def get_value(self):
        pass

    def create_control_widget(self):
        pass


class NumericControl(ParameterControl):
    """ Widget for float parameters
    """

    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter.default))

        # TODO Add validator
        # validator = QDoubleValidator(*self.parameter.bounds, 3)
        # control_widget.setValidator(validator)
        return control_widget

    def get_value(self):
        return float(self.control_widget.text())


class IntegerControl(ParameterControl):
    """ Widget for integer parameters
        """

    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter.default))

        # TODO Add validator
        # validator = QIntValidator(*self.parameter.bounds)
        # control_widget.setValidator(validator)
        return control_widget

    def get_value(self):
        return int(self.control_widget.text())


class StringControl(ParameterControl):
    """ Widget for string parameters
        """

    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter.default))
        return control_widget

    def get_value(self):
        return self.control_widget.text()


class ListControl(ParameterControl):
    """ Widget for listselect parameters
        """

    def create_control_widget(self):
        control_widget = QComboBox()
        if not self.parameter.check_on_set:
            control_widget.setEditable(True)
        # Add list and set default:
        control_widget.addItems(self.parameter.objects)
        control_widget.setCurrentIndex(control_widget.findText(self.parameter.default))

        return control_widget

    def get_value(self):
        return self.control_widget.currentText()


if __name__ == '__main__':
    from stytra.metadata import MetadataFish, MetadataLightsheet

    app = QApplication([])

    metadata_gui = MetadataGui(parameterized=MetadataLightsheet())
    metadata_gui.show()
    app.exec_()
