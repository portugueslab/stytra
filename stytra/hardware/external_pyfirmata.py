try:
    import pyfirmata as pyfi
except ImportError:
    print("Pyfirmata is not installed")

# direct mode to call pins with pyfirmata
from time import sleep

MODE_DICT = dict(input=pyfi.INPUT, output=pyfi.OUTPUT, pwm=pyfi.PWM, servo=pyfi.SERVO)
AD_ATTR_DICT = dict(a="analog", d="digital")


class PyfirmataConnection:
    """Using StandardFirmata and pyfirmata to control an Arduino board with Python"""

    def __init__(self, com_port, layout, iterator=True):
        """If using analog ports is handy to start an iterator thread"""

        self.board = pyfi.Arduino(com_port)
        print("Connection successfully established")
        sleep(1)

        # Convert configuration list of dictionaries in a dictionary of configurations:
        self.layout = dict()
        for pin_conf in layout:
            pin_conf["mode"] = MODE_DICT[pin_conf["mode"]]
            self.layout[pin_conf.pop("pin")] = pin_conf

        if iterator:
            self.it = pyfi.util.Iterator(self.board)
            self.it.start()

        self.initialize()

    def initialize(self):
        """ """
        for pin_n, pin_conf in self.layout.items():
            getattr(self.board, AD_ATTR_DICT[pin_conf["ad"]])[pin_n].mode = pin_conf[
                "mode"
            ]

    def read(self, pin_n):
        """Access and read from a pin.

        Parameters
        ----------
        pin_n : int
            Integer indicating pin to be read

        Returns
        -------
        float or int

        """

        pin_conf = self.layout[pin_n]
        value = getattr(self.board, AD_ATTR_DICT[pin_conf["ad"]])[pin_n].read()

        return value

    def read_all(self):
        """Read all pins that are set as inputs

        Returns
        -------
        list of floats or ints

        """
        return [
            self.read(pin_n)
            for pin_n, pin_conf in self.layout.items()
            if pin_conf["mode"] == "input"
        ]

    def write(self, pin_n, value):
        """

        Parameters
        ----------
        pin_n:
            Integer indicating pin to be written

        Returns
        -------

        """
        pin_conf = self.layout[pin_n]
        sel_pins = getattr(self.board, AD_ATTR_DICT[pin_conf["ad"]])[pin_n]
        sel_pins.write(value)

    def write_multiple(self, pin_values_dict):
        for pin_n, value in pin_values_dict.items():
            self.write(pin_n, value)
        return True

    def close(self):
        """Close connection"""

        self.board.exit()
        return print("Communication successfully interrupted")


if __name__ == "__main__":
    LAYOUT = (dict(pin=5, mode="pwm", ad="d"), dict(pin=11, mode="pwm", ad="d"))

    write_multiple = {5: 0.4, 11: 1.0}

    try_pumps = PyfirmataConnection(com_port="COM3", layout=LAYOUT)

    # try_pumps.close()

    # sleep(5)
    try_pumps.write_multiple(write_multiple)
    print("sending pulse")
