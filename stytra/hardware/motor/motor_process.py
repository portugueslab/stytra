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
import deepdish as dd
import pandas as pd

duration = 100
class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        cam = SpinnakerCamera()
        cam.open_camera()
        cam.set("exposure", 30)
        start = datetime.datetime.now()

        # center_y = 270
        # center_x = 360

        while True:
            start_grabbing = datetime.datetime.now()
            image_converted = cam.read()
            # grab.append((datetime.datetime.now() - start_grabbing).total_seconds())
            if image_converted is not None:
                start = datetime.datetime.now()
                # print("shape: {}".format(image_converted.shape))
                cv2.imshow("img", image_converted)
                cv2.waitKey(1)

                # identify dot
                blobdet = cv2.SimpleBlobDetector_create()
                keypoints = blobdet.detect(image_converted)
                kps = np.array([k.pt for k in keypoints])
                # print(kps)

                point_x = int(kps[0][0])
                point_y = int(kps[0][1])

                # i = random.randint(1, 4400000)
                self.position_queue.put((point_x, point_y))
                # comp.append((datetime.datetime.now() - start).total_seconds())

            if (datetime.datetime.now() - start).total_seconds() > duration:
                break


class ReceiverProcess(Process):
    def __init__(self, position_queue, finished_event):
        super().__init__()
        self.position_queue = position_queue
        self.motor_position_queue = Queue()
        self.finished_event = finished_event

    def run(self):
        mottione = Motor(1)
        mottitwo = Motor(2)
        mc = MotorCalibrator(mottione, mottitwo)

        mottione.open()
        mottitwo.open()

        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()
        stage_at_x =[]
        stage_at_y =[]
        dot_at_x = []
        dot_at_y = []
        time =[]

        while not self.finished_event.is_set():

            pos = None
            while True:
                try:
                    pos = self.position_queue.get(timeout=0.001)
                except Empty:
                    break
            if pos is not None:
                # print("from queue:", pos[0], pos[1])
                pos_x = mottitwo.get_position()
                stage_at_x.append(pos_x)
                pos_y = mottione.get_position()
                stage_at_y.append(pos_y)

                connx, conny = mc.calculate(pos[0], pos[1])
                # print (connx, conny, distx, disty)
                con = pos_x + connx
                mottitwo.movesimple(con)

                cony = pos_y + conny
                mottione.movesimple(cony)

                dot_at_x.append(pos[0])
                dot_at_y.append(pos[1])

                # print("time since last ", (datetime.datetime.now() - prev_event_time).total_seconds())
                time.append((datetime.datetime.now() - start).total_seconds())
                # prev_event_time = datetime.datetime.now()
                # print("Retrieved position x: {}".format(pos[0]))
                # print("Retrieved position y: {}".format(pos[1]))

            if (datetime.datetime.now() - start).total_seconds() > duration:
                dd.io.save("stage_movement.h5", pd.DataFrame(dict(stage_x=stage_at_x,
                                                                  stage_y =stage_at_y,
                                                                  dot_x =dot_at_x,
                                                                  dot_y=dot_at_y,
                                                                  time_passed = time)))
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