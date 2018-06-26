import serial as com


class SerialConnection:
    """ """

    def __init__(self, com_port=None, baudrate=None):
        self.conn = com.Serial(port=com_port)
        print(self.conn)

        if baudrate:
            self.conn.baudrate = baudrate

    def read(self):
        """ """
        i = self.conn.read()
        return self.convert(i)

    def write(self, what):
        """

        Parameters
        ----------
        what :
            

        Returns
        -------

        """
        self.conn.write(what.encode())

    def convert(self, i):
        """

        Parameters
        ----------
        i :
            

        Returns
        -------

        """
        return unpack("<b", i)[0]

    def __del__(self):
        self.conn.close()


class PyboardConnection(SerialConnection):
    """ """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
