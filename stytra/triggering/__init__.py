import serial as com
import time
import zmq
from datetime import datetime


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
        self.write('set'+str(fn))
        #print('set'+str(fn))
        #self.write('set20')


class ZmqClient:
    def __init__(self, tcp_address='tcp://192.168.233.156:5555', timeout_time=3):
        self.context = zmq.Context()
        self.tcp_address = tcp_address

        #  Socket to talk to server
        print('Connecting to:' + tcp_address)
        self.socket = self.context.socket(zmq.REQ)
        self.timeout_time = timeout_time


    def send(self, message=None):

        self.socket.connect(self.tcp_address)
        self.socket.send(bytes(message))

        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        if poller.poll(self.timeout_time * 1000):  # timeout in milliseconds
            #  Get the reply.
            return self.socket.recv()
        else:
            print("Timeout processing request! (start LabView program?)")





    # still untested
    # def test_velocity(self):
    #     sendtime = datetime.now()
    #     for request in range(1):
    #
    #         socket.send(b"start")
    #
    #         #  Get the reply.
    #         message = socket.recv()
    #
    #     rectime = datetime.now()
    #     print("Latency is {:.2f}".format((rectime-sendtime).total_seconds()*1000))


class ZmqLightsheetTrigger(ZmqClient):
    def __init__(self, pause=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pause = pause


    def prepare(self):
        self.send(b"prepare")

    def start_command(self):
        self.send(b"start")

    def stop(self):
        self.send(b"stop")

    def start(self):
        self.send(b"prepare")
        time.sleep(self.pause)
        self.send(b"start")

    def get_ls_data(self):
        return self.send(b"")
