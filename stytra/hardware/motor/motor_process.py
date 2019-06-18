from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import numpy as np


class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        for i in range(10):
            self.position_queue.put(np.random.rand())
            sleep(0.01)


class ReceiverProcess(Process):
    def __init__(self, position_queue):
        super().__init__()
        self.position_queue = position_queue

    def run(self):
        start = datetime.datetime.now()

        while True:
            try:
                pos = self.position_queue.get(timeout=0.01)
                print("Retrieved position: {}".format(pos))
            except Empty:
                pass

            #print((datetime.datetime.now() - start).total_seconds())
            if (datetime.datetime.now() - start).total_seconds() > 5:
                break

if __name__ == '__main__':
    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()
    source.join()
    receiver.join()