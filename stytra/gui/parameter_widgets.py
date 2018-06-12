from PyQt5.QtWidgets import QDoubleSpinBox, QWidget, QLabel


class ParameterSpinBox(QDoubleSpinBox):
    """ """
    def __init__(self, *args, parameter, **kwargs):
        super().__init__(*args, **kwargs)
        self.parameter = parameter
        param_state = parameter.saveState()
        self.setValue(param_state['value'])
        self.setMinimum(param_state['limits'][0])
        self.setMaximum(param_state['limits'][1])
        self.parameter.sigValueChanged.connect(self.update_val)
        self.valueChanged.connect(self.set_param_val)

    def set_param_val(self):
        """ """
        self.parameter.setValue(self.value())

    def update_val(self):
        """ """
        self.setValue(self.parameter.value())
