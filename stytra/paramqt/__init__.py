from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, \
    QLabel, QLineEdit, QPushButton, QComboBox
from PyQt5.QtGui import QIntValidator, QDoubleValidator
import param
from param.parameterized import classlist


class ParameterGui(QWidget):
    """
    Widget for displaying metadata controls.
    """

    def __init__(self, metadata_obj=None,  *args, **kwargs):
        """ Constructor

        :param metadata_obj: Metadata object
        """

        super().__init__(*args, **kwargs)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.parameter_controls = []
        self.metadata_obj = metadata_obj

        # Add controls for all the parameters:
        for param_name in self.metadata_obj.params().keys():
            if not param_name == 'name':
                self.add_parameter_to_gui(param_name)

        # Connect ok button for saving data:
        ok_butt = QPushButton("Save Metadata")
        ok_butt.clicked.connect(self.save_meta)
        self.layout.addWidget(ok_butt)

    def add_parameter_to_gui(self, param_name):
        """ Add a new control to the widget.
        :param param_name: name of the parameter to add (string)
        """
        # It may be changed, since the gui right now have all and only the
        # entries of the parameterized object, no other things are addable.

        param_obj = self.metadata_obj.params(param_name)
        widget_class = ParameterGui.get_widget_type(param_obj)
        new_control = widget_class(self.metadata_obj, param_name)

        self.parameter_controls.append(new_control)
        self.layout.addWidget(new_control)

    def save_meta(self):
        """ Parse metadata from the GUI and close it only if all are valid
        """
        validity_check = True
        for parameter_control in self.parameter_controls:
            if not isinstance(parameter_control, StaticControl):
                try:
                    setattr(self.metadata_obj, parameter_control.name, parameter_control.get_value())
                except ValueError:
                    parameter_control.setStyleSheet('background-color: rgb(120, 40, 40)')
                    parameter_control.show()
                    validity_check = False

            #if validity_check:
                #self.close()

    @staticmethod
    def get_widget_type(param_obj):
        """
        Function that returns the appropriate control class
        for each data type
        """
        # map of param types over control classes:
        param_map_to_widget = {
            param.String: StringControl,
            param.Number: NumericControl,
            param.Integer: IntegerControl,
            param.ObjectSelector: ListControl
        }

        if param_obj.constant:
            return StaticControl
        else:
            for t in classlist(type(param_obj))[::-1]:
                if t in param_map_to_widget:
                    return param_map_to_widget[t]


class ParameterControl(QWidget):
    """
    Class for the single parameters controls of the metadata GUI
    """
    def __init__(self, parameterized_obj, name, *args, **kwargs):
        """ Constructor
        :param parameterized_obj: parameterized object containing the desired parameter
        :param name: name of the parameter (string)
        """
        # Note: here the parameterized object has to be passed because the
        # parameter object itself seems not to contain its current value,
        # only the default one.

        super().__init__(*args, **kwargs)
        parameter_obj = parameterized_obj.params(name)
        assert isinstance(parameter_obj, param.Parameter)  # Check input

        self.name = name
        self.label = self._pretty_print(name)
        self.parameter = parameter_obj
        self.parameter_val = getattr(parameterized_obj, name)

        # Create layout and add label to the control:
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(QLabel(self.label))

        # Create control widget according to parameter type:
        self.control_widget = self.create_control_widget()
        self.layout.addWidget(self.control_widget)

    def get_value(self):
        pass

    def create_control_widget(self):
        pass

    @staticmethod
    def _pretty_print(s):
        n = s.replace("_", " ")
        n = n.capitalize()
        return n


class NumericControl(ParameterControl):
    """ Widget for float parameters
    """

    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter_val))

        if self.parameter.constant:
            control_widget.setReadOnly(True)

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
        control_widget = QLineEdit(str(self.parameter_val))

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
        control_widget = QLineEdit(str(self.parameter_val))

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
        control_widget.setCurrentIndex(control_widget.findText(self.parameter_val))

        return control_widget

    def get_value(self):
        return self.control_widget.currentText()


class StaticControl(ParameterControl):
    """ Widget for unmodifiable parameters
    """
    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter_val))
        control_widget.setReadOnly(True)

        # Display this widget in gray:
        control_widget.setStyleSheet('background-color: gray ')

        return control_widget

    def get_value(self):
        return self.parameter_val


if __name__ == '__main__':
    from stytra.metadata import MetadataLightsheet

    app = QApplication([])
    lightsheetmeta = MetadataLightsheet()
    lightsheetmeta.piezo_frequency = 8
    metadata_gui = ParameterGui(lightsheetmeta)
    metadata_gui.show()
    app.exec_()
