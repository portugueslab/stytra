# stuff from Andreas's code

# Initialize pyboard and turn the camera off
class uc:
    def __init__(self, comport, baudrate=None):
        self.conn = com.Serial(port=comport)

        if baudrate:
            self.conn.baudrate = baudrate

    def read(self):
        i = self.conn.read()
        v = self.convert(i)

        return v

    def write(self, what):
        self.conn.write(what.encode())

    def convert(self, i):
        return unpack("<b", i)[0]

    def __del__(self):
        self.conn.close()


pyb = uc('COM3')
pyb.write('off')

# triggering starts
pyb.write('on')