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
from stytra.tracking.fish import FishTrackingMethod


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
        self.thres = 10000

    def run(self):
        mottione = Motor(1)
        mottitwo = Motor(2)
        mottione.open()
        mottitwo.open()
        output_type = namedtuple("stagexy", ["x_", "y_"])

        dt = datetime.datetime.now()
        pos = None
        while not self.finished_event.is_set():

            try:
                pos = self.position_queue.get(timeout=0.001)
            except Empty:
                pass
            if pos is not None:
                try:
                    pos_x = mottitwo.get_position()
                    pos_y = mottione.get_position()
                    time = datetime.datetime.now()
                    center_y = 270
                    center_x = 360

                    distance_x = int(center_x - pos[1][0])
                    distance_y = int(center_y - pos[1][1])

                    connx = int(distance_x * 909)
                    conny = int(distance_y * 1052)

                    conx = pos_x + connx
                    dstx = distance.euclidean(conx, pos_x)
                    if dstx >= self.thres:
                        mottitwo.movesimple(conx)

                    cony = pos_y + conny
                    dsty = distance.euclidean(cony, pos_y)
                    if dsty >= self.thres:
                        mottione.movesimple(cony)

                    e = (float(pos_x), float(pos_y))

                except (TypeError, IndexError):
                    e = (0.0, 0.0)

                self.motor_position_queue.put(time, output_type(*e))
        mottitwo.close()
        mottione.close()


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
