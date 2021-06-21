import nidaqmx

from stytra.hardware.devices.interface import Board

class NIBoard(Board):
    """Class for controlling an NI board.

    Uses the nidaqmx API to interact with NI-DAQmx driver.
    """

    def __init__(self, device, channel, min_val, max_val,  **kwargs):

        self.dev = dev
        self.chan = chan
        self.min_val = min_val
        self.max_val = max_val

    super().__init__(**kwargs)

    def start_ao_task(self):
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_current_chan()