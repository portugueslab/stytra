from stytra.stimulation.stimuli import Stimulus
from stytra.hardware.external_pyfirmata import PyfirmataConnection


class WriteArduinoPin(Stimulus):
    """Simple class to write a value on an arduino pin. Mostly a simple example to implement
    your own fancy arduino classes.

    Parameters
    ----------
    pin : int
        Pin number.
    value : float or int
        Value to be set on the pin.
    """

    name = "set_arduino_pin"

    def __init__(self, pin_values_dict, *args, **kwargs):
        self.pin_values = pin_values_dict
        super().__init__(*args, **kwargs)

    def start(self):
        super().start()
        self._experiment.arduino_board.write_multiple(self.pin_values)


