from multiprocessing import Process, Event, Value
from pathlib import Path
import datetime
import time


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
    trigger = Crappy2PTrigger(pathname=r'C:\Users\lpetrucco\Desktop\dummydir')
    dest = SigReceiver(trigger.start_event)
    trigger.start()
    dest.start()
