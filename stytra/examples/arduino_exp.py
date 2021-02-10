from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.set_arduino_pin import WriteArduinoPin

LAYOUT = (dict(pin=5, mode="pwm", ad="d"),
              dict(pin=11, mode="pwm", ad="d"))


class MotorProtocol(Protocol):
    name = 'motor_protocol'

    def get_stim_sequence(self):
        stimuli = [
            WriteArduinoPin(port='COM3', layout=LAYOUT, pin=5, value=0.8, duration=4.0),
            WriteArduinoPin(port='COM3', layout=LAYOUT, pin=5, value=0)
        ]
        return stimuli


if __name__ == "__main__":

    st = WriteArduinoPin(port='COM3', layout=LAYOUT, pin=5, value=0.8, duration=4.0)
    #Stytra(protocol=MotorProtocol())