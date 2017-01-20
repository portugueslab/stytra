import serial as com


class SerialConnection:
    def __init__(self, com_port, baudrate=None):
        self.conn = com.Serial(port=com_port)

        if baudrate:
            self.conn.baudrate = baudrate

    def read(self):
        i = self.conn.read()
        return self.convert(i)

    def write(self, what):
        self.conn.write(what.encode())

    def convert(self, i):
        return unpack("<b", i)[0]

    def __del__(self):
        self.conn.close()


class PyboardConnection(SerialConnection):

    def switch_on(self):
        self.write('on')

    def switch_off(self):
        self.write('off')

    def set_pulse_freq(self, fn):
        self.write(str(fn))
