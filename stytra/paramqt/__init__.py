from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, \
    QLabel, QLineEdit, QPushButton, QComboBox, QSlider
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator
import param
from param.parameterized import classlist


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
        self.widget_label = QLabel(self.label)
        self.layout.addWidget(self.widget_label)

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


class NumericControlSliderCombined(ParameterControl):
    """ Widget for float parameters
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numeric_control_widget = self.create_numeric_control_widget()
        self.layout.addWidget(self.numeric_control_widget)

        self.control_widget.valueChanged.connect(self.update_numeric)
        self.numeric_control_widget.editingFinished.connect(self.update_slider)

    def create_control_widget(self):
        slider_control_widget = QSlider(Qt.Horizontal)
        slider_control_widget.setValue(int((-self.parameter.bounds[0] + self.parameter_val /
                                            (self.parameter.bounds[1]-self.parameter.bounds[0])*1000)))
        slider_control_widget.setMaximum(1000)

        return slider_control_widget

    def create_numeric_control_widget(self):
        numeric_control_widget = QLineEdit(str(self.parameter_val))
        return numeric_control_widget

    def update_numeric(self):
        val = self.get_value()
        self.numeric_control_widget.setText(str(val))

    def update_slider(self):
        val = self.get_numeric_value()
        self.control_widget.setValue(int((-self.parameter.bounds[0] + val /
                                          (self.parameter.bounds[1] - self.parameter.bounds[0]) * 1000)))

    def get_value(self):
        return self.parameter.bounds[0] + self.control_widget.value() / 1000 * \
                     (self.parameter.bounds[1] - self.parameter.bounds[0])

    def get_numeric_value(self):
        return float(self.numeric_control_widget.text())


class NumericControl(ParameterControl):
    """ Widget for float parameters
    """

    def create_control_widget(self):
        control_widget = QLineEdit(str(self.parameter_val))

        # TODO Add validator
        # validator = QDoubleValidator(*self.parameter.bounds, 3)
        # control_widget.setValidator(validator)
        return control_widget

    def get_value(self):
        return float(self.control_widget.text())


class NumericControlSlider(ParameterControl):
    """ Widget for float parameters
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control_widget.valueChanged.connect(self.update_label)
        self.update_label()

    def create_control_widget(self):
        control_widget = QSlider(Qt.Horizontal)
        control_widget.setValue(int((-self.parameter.bounds[0] + self.parameter_val /
                                    (self.parameter.bounds[1]-self.parameter.bounds[0])*1000)))
        control_widget.setMaximum(1000)

        return control_widget

    def get_value(self):
        return self.parameter.bounds[0] + self.control_widget.value() / 1000 * \
                     (self.parameter.bounds[1]-self.parameter.bounds[0])

    def update_label(self):
        self.widget_label.setText(self.label+' {:.2f}'.format(self.get_value()))


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


# class IntegerControlSlider(NumericControlSlider):
#     def create_control_widget(self):
#         control_widget = QSlider(Qt.Horizontal)
#         control_widget.setValue(self.parameter.default)
#         control_widget.setMinimum(self.parameter.bounds[0])
#         control_widget.setMaximum(self.parameter.bounds[1])
#
#         return control_widget
#
#     def get_value(self):
#         return  self.control_widget.value()
#
#     def update_label(self):
#         self.widget_label.setText(self.label+' {}'.format(self.get_value()))


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


class ParameterGui(QWidget):
    """
    Widget for displaying metadata controls.
    """

    # map of param types over control classes:
    param_map_to_widget = {
        param.String: StringControl,
        param.Number: NumericControlSliderCombined,
        param.Integer: IntegerControl,
        param.ObjectSelector: ListControl
    }

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

        if validity_check:
            self.close()

    @staticmethod
    def get_widget_type(param_obj):
        """
        Function that returns the appropriate control class
        for each data type
        """
        if param_obj.constant:
            return StaticControl
        else:
            for t in classlist(type(param_obj))[::-1]:
                if t in ParameterGui.param_map_to_widget:
                    return ParameterGui.param_map_to_widget[t]




if __name__ == '__main__':
    from stytra.metadata import MetadataLightsheet, MetadataFish

    app = QApplication([])
    lightsheetmeta = MetadataFish()
    lightsheetmeta.piezo_frequency = 8
    metadata_gui = ParameterGui(lightsheetmeta)
    metadata_gui.show()
    app.exec_()
