from multiprocessing import Process, Event, Value
from pathlib import Path
import datetime
import time
import zmq


class Trigger(Process):

    def __init__(self):
        super().__init__()

        self.start_event = Event()
        self.t = datetime.datetime.now()
        self.kill_event = Event()
        self.running_flag = Value("i", 1)

    def check_trigger(self):
        return False

    def run(self):
        while True:
            self.kill_event.wait(0.0001)
            if self.kill_event.is_set():
                break
            if self.check_trigger():
                self.start_event.set()
                self.t = datetime.datetime.now()
            else:
                if self.start_event.is_set():
                    # Keep the signal on for at least 0.1 s
                    time.sleep(0.1)
                    self.start_event.clear()


# class ZmqTrigger(Process):
#
#     def __init__(self, port='5555'):
#         self.zmq_context = zmq.Context()
#         self.zmq_socket = self.zmq_context.socket(zmq.REP)
#         self.zmq_socket.bind("tcp://*:{}".format(port))
#         super().__init__()
#
#     def check_trigger(self):
#         self.lightsheet_config = self.zmq_socket.recv_json()
#         print(self.lightsheet_config)

class ZmqTrigger(Trigger):
    def __init__(self, port):
        self.port = port
        super().__init__()

    def check_trigger(self):
        self.lightsheet_config = self.zmq_socket.recv_json()
        self.zmq_socket.send_json(5)

        return True

    def run(self):
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REP)
        self.zmq_socket.bind("tcp://*:{}".format(self.port))
        self.zmq_socket.setsockopt(zmq.RCVTIMEO, -1)

        super().run()


class Crappy2PTrigger(Trigger):
    def __init__(self, pathname):
        self.path = Path(pathname)
        self.files_n = len(list(self.path.glob('*')))
        super().__init__()

    def check_trigger(self):
        n = len(list(self.path.glob('*')))
        if n != self.files_n:
            self.files_n = n
            return True
        else:
            return False


if __name__=='__main__':
    port = '5555'
    trigger = ZmqTrigger(port)
    trigger.start()
