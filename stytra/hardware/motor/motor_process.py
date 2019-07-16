from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import numpy as np
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import cv2
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple
from stytra.collectors.namedtuplequeue import NamedTupleQueue
from scipy.spatial import distance


class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = NamedTupleQueue()

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

                    e = (point_x, point_y)

            except (TypeError, IndexError):
                e = (None, None)

            self.position_queue.put(datetime.datetime.now(), output_type(*e))



class ReceiverProcess(Process):
    def __init__(self, dot_position_queue, finished_event, motor_position_queue):
        super().__init__()
        self.position_queue = dot_position_queue
        self.motor_position_queue = motor_position_queue
        self.finished_event = finished_event
        self.thres = 5

    def run(self):
        motor_y = Motor(1, scale=250)
        motor_x = Motor(2, scale=183)
        center_y = 270
        center_x = 360
        motor_y.open()
        motor_x.open()
        output_type = namedtuple("stagexy", ["x_", "y_", "dist_x", "dist_y"])
        last_position = None
        dot_pos = []
        motor_pos =[]
        times = []

        while not self.finished_event.is_set():

            try:
                tracked_time, last_position = self.position_queue.get(timeout=0.001)
            except Empty:
                pass

            if last_position is not None:
                time = datetime.datetime.now()
                times.append(time)
                pos_x = motor_x.get_position()
                pos_y = motor_y.get_position()
                motor_pos.append([pos_x, pos_y])
                try:
                    distance_x = center_x - last_position.f0_x
                    distance_y = center_y - last_position.f0_y

                    if distance_x**2 + distance_y**2 > self.thres**2:
                        print("Moving")
                        motor_x.move_relative(distance_x)
                        motor_y.move_relative(distance_y)
                        print (distance_x, distance_y)
                        dot_pos.append([distance_x,distance_y])

                    e = (float(pos_x), float(pos_y), distance_x, distance_y)

                except (ValueError, TypeError, IndexError):
                    e = (pos_x, pos_y, 0., 0.)

                self.motor_position_queue.put(time, output_type(*e))
                dd.io.save("stage_movement.h5", pd.DataFrame(dict(time = times,
                                                                  dots=dot_pos,
                                                                  motorpos=motor_pos)))
        motor_x.close()
        motor_y.close()


################################


if __name__ == '__main__':
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

