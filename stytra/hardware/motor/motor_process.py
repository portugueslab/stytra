from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
import numpy as np
from stytra.hardware.motor.stageAPI import Motor
#import random
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
from stytra.hardware.motor.motor_calibrator import MotorCalibrator
import cv2


class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        cam = SpinnakerCamera()
        cam.open_camera()
        cam.set("exposure", 12)

        center_y = 270
        center_x = 360

        for i in range(0, 10):
            start_grabbing = datetime.datetime.now()
            image_converted = cam.read()
            print("Grabbing timing:", (datetime.datetime.now() - start_grabbing).total_seconds())
            start = datetime.datetime.now()
            # cv2.imshow("img", image_converted)
            # cv2.waitKey(600)

            # identify dot
            blobdet = cv2.SimpleBlobDetector_create()
            keypoints = blobdet.detect(image_converted)
            kps = np.array([k.pt for k in keypoints])
            # print(kps)

            point_x = int(kps[0][0])
            point_y = int(kps[0][1])

            distance_x = int(center_x - point_x)
            distance_y = int(center_y - point_y)

            conx = abs(distance_x)
            cony = abs(distance_y)
            connx = int(conx * 1666)
            conny = int(cony * 1666)

            # i = random.randint(1, 4400000)
            self.position_queue.put([connx, conny, distance_x, distance_y])
            print("Real function timing:", (datetime.datetime.now() - start).total_seconds())



class ReceiverProcess(Process):
    def __init__(self, position_queue):
        super().__init__()
        self.position_queue = position_queue

    def run(self):

        mottione = Motor(1)
        mottitwo = Motor(2)
        mc = MotorCalibrator()

        mottione.open()
        mottitwo.open()

        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()

        while True:
            try:
                pos = self.position_queue.get(timeout=0.01)
                pos_x = mottitwo.get_position()
                pos_y = mottione.get_position()

                mc.track_dot(pos_x, pos_y, pos[0], pos[1], pos[2], pos[3])

                print("time since last ", (datetime.datetime.now() - prev_event_time).total_seconds())
                prev_event_time = datetime.datetime.now()
                print("Retrieved position x: {}".format(pos[0]))
                print("Retrieved position y: {}".format(pos[1]))


            except Empty:
                pass

            if (datetime.datetime.now() - start).total_seconds() > 5:
                break

        mottitwo.close()
        mottione.close()


################################


if __name__ == '__main__':

    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()
    source.join()
    receiver.join()