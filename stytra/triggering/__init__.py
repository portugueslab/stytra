import time
import zmq
from stytra.hardware.serial import PyboardConnection
from datetime import datetime


class PyboardTrigger(PyboardConnection):

    def switch_on(self):
        self.write('on')

    def switch_off(self):
        self.write('off')

    def set_pulse_freq(self, fn):
        # self.write('set'+str(fn))
        self.write('set20')