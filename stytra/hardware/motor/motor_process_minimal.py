from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import numpy as np
from stytra.hardware.motor.stageAPI import Motor
import random
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
from stytra.hardware.motor.motor_calibrator import MotorCalibrator
import cv2


class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        start = datetime.datetime.now()
        for i in range(0, 10):
            i = random.randint(22300, 330000)
            j = random.randint(22300, 330000)
            self.position_queue.put([i,j])
            print("Real function timing:", (datetime.datetime.now() - start).total_seconds())
            sleep(0.02)



class ReceiverProcess(Process):
    def __init__(self, position_queue):
        super().__init__()
        self.position_queue = position_queue

    def run(self):
        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()
        mottione = Motor(1)
        mottitwo = Motor(2)
        #mottione.homethatthing()
        mottione.open()
        mottitwo.open()
        #mottione.setvelocity(204552, 107374182)
        time =[]

        while True:
            try:
                pos = self.position_queue.get(timeout=1)
                time.append((datetime.datetime.now() - prev_event_time).total_seconds())
                prev_event_time = datetime.datetime.now()
                mottione.movethatthing(pos[1])
                mottitwo.movethatthing(pos[0])
                # print("Retrieved position x : {}".format(pos[0]))
                # print("Retrieved position x : {}".format(pos[1]))
                sleep(0.04)

            except Empty:
                pass

            if (datetime.datetime.now() - start).total_seconds() > 10:
                mottione.close()
                mottitwo.close()
                print(time)
                break

################################


if __name__ == '__main__':

    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()
    source.join()
    receiver.join()