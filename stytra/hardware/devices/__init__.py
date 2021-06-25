try:
    import nidaqmx
except ImportError:
    print('nidaqmx is not installed')

from stytra.hardware.devices.interface import Board

class NIBoard(Board):
    """Class for controlling an NI board.

    Uses the nidaqmx API to interact with NI-DAQmx driver.
    """

    def __init__(self, dev, chan, min_val, max_val,  **kwargs):

        self.dev = dev
        self.chan = chan
        self.min_val = min_val
        self.max_val = max_val

    super().__init__(**kwargs)

    def initialize(self):
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan("{}/{}".format(self.dev, self.chan),
                                                  min_val=self.min_val, max_val=self.max_val)

    def write(self, voltage):
        self.voltage = voltage
        self.task.write(self.voltage)