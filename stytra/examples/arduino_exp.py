from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.arduino import WriteArduinoPin
from lightparam import Param


# Example showcasing a protocol that uses an arduino and sets a pin value on it. For more sophisticate
# applications you want to subclass the WriteArduinoPin class.
class ArduinoProtocol(Protocol):
    name = "arduino_protocol"
    stytra_config = dict(
        arduino_config=dict(
            com_port="COM3",
            layout=[dict(pin=11, mode="pwm", ad="d"), dict(pin=5, mode="pwm", ad="d")],
        )
    )

    def __init__(self):
        super(ArduinoProtocol, self).__init__()
        self.pin_on_period = Param(1.0, limits=(0.0, 1000.0), unit="s", loadable=False)
        self.power_in = Param(0.5, limits=(0.0, 1.0))
        self.power_out = Param(0.5, limits=(0.0, 1.0))

    def get_stim_sequence(self):
        stimuli = [
            WriteArduinoPin(
                pin_values_dict={5: self.power_in, 11: self.power_out},
                duration=self.pin_on_period,
            ),
            WriteArduinoPin(pin_values_dict={5: 0.0, 11: 0.0}, duration=1),
        ]
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=ArduinoProtocol())
