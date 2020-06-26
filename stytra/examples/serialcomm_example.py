from stytra import Stytra, Protocol
from stytra.stimulation.stimuli.generic_stimuli import Stimulus
from stytra.stimulation.stimuli.visual import Pause
from stytra.hardware.serial import SerialConnection


class ArduinoCommStimulus(Stimulus):
    def __init__(self, com_port="COM3", baudrate=115200, **kwargs):
        super().__init__(**kwargs)
        self._pyb = None
        self.com_port = com_port
        self.baudrate = baudrate

    def initialise_external(self, experiment):

        # Initialize serial connection and set it as experiment attribute to make
        # it available for other stimuli:
        try:
            self._pyb = getattr(experiment, "_pyb")
        except AttributeError:
            experiment._pyb = SerialConnection(
                com_port=self.com_port, baudrate=self.baudrate
            )
            self._pyb = getattr(experiment, "_pyb")

    def start(self):
        """ """
        self._pyb.write("b")  # send blinking command at stimulus start


class ArduinoCommProtocol(Protocol):
    name = "arduino_comm_protocol"  # every protocol must have a name.

    stytra_config = dict(camera=dict(type="ximea"), tracking=dict(method="tail"))

    def get_stim_sequence(self):
        # This is the
        stimuli = []
        for i in range(5):
            stimuli.append(Pause(duration=4))
            stimuli.append(ArduinoCommStimulus(duration=0))
        return stimuli


if __name__ == "__main__":
    st = Stytra(protocol=ArduinoCommProtocol())
