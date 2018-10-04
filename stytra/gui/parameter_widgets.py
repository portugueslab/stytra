from PyQt5.QtWidgets import QDoubleSpinBox, QWidget, QLabel
from poparam.gui import ControlSpin


class ParameterSpinBox(QDoubleSpinBox):
    """ """

    def __init__(self, *args, parameter, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameter = parameter
        self.setValue(parameter.value)
        self.setMinimum(parameter.limits[0])
        self.setMaximum(parameter.limits[1])
        self.parameter.sigValueChanged.connect(self.update_val)
        self.valueChanged.connect(self.set_param_val)

    def set_param_val(self):
        """ """
        self.parameter.setValue(self.value())

    def update_val(self):
        """ """
        self.setValue(self.parameter.value())
