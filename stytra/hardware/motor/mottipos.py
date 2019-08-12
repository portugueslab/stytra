from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import numpy as np
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import cv2
import deepdish as dd
import pandas as pd
from collections import namedtuple

#############################################

duration = 10


class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        cam = SpinnakerCamera()
        cam.open_camera()
        cam.set("exposure", 30)
        start = datetime.datetime.now()
        output_type = namedtuple("dotxy", ["x", "y"])

        while True:
            try:
                im = cam.read()
                if im is not None:
                    start = datetime.datetime.now()
                    cv2.imshow("img", im)
                    cv2.waitKey(1)

                    idxs = np.unravel_index(np.nanargmin(im), im.shape)
                    e = (np.float(idxs[1]), np.float(idxs[0]))

                    point_x = e[0]
                    point_y = e[1]

                    self.position_queue.put((point_x, point_y))

            except (TypeError, IndexError):
                pass


class ReceiverProcess(Process):
    def __init__(self, position_queue, finished_event):
        super().__init__()
        self.position_queue = position_queue
        self.finished_event = finished_event
        self.thres = 5

    def run(self):
        motor_y = Motor(1, scale=1052)
        motor_x = Motor(2, scale=909)
        center_y = 270
        center_x = 360
        motor_y.open()
        motor_x.open()

        last_position = None
        dot_pos = []
        motor_pos = []
        times = []
        start = datetime.datetime.now()

        while not self.finished_event.is_set():

            try:
                pos = self.position_queue.get(timeout=0.001)
                print("gotten positions", pos)

                times.append((datetime.datetime.now() - start).total_seconds())
                pos_x = motor_x.get_position()
                pos_y = motor_y.get_position()
                motor_pos.append([pos_x, pos_y])
                try:
                    distance_x = center_x - pos[0]
                    distance_y = center_y - pos[1]

                    if distance_x ** 2 + distance_y ** 2 > self.thres ** 2:
                        motor_x.move_relative(distance_x)
                        motor_y.move_relative(distance_y)
                        print("distances", distance_x, distance_y)
                        dotposx = motor_x.move_relative_without_move(distance_x)
                        dotposy = motor_x.move_relative_without_move(distance_y)
                        dot_pos.append([dotposx, dotposy])

                except (ValueError, TypeError, IndexError):
                    pass

            except Empty:
                pass

            if (datetime.datetime.now() - start).total_seconds() > duration:
                print(len(times), len(dot_pos), len(motor_pos))

                df = pd.DataFrame(dict(time=times, dots=dot_pos, motorpos=motor_pos))
                df.to_pickle("my_file.pkl")
                motor_x.close()
                motor_y.close()


################################

if __name__ == "__main__":
    event = Event()
    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue, finished_event=event)
    source.start()
    receiver.start()

    finishUp = True
    sleep(20)
    event.set()
    source.join()
    receiver.join()
