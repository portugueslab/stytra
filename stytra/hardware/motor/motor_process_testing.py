from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import random
import cv2
import numpy as np
import pandas as pd
import deepdish as dd



class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

        self.l = [100, 3000, 1500,30000, 80]

    def run(self):
        start = datetime.datetime.now()
        # for i in range(0, 10):
        #     i = random.randint(22300, 330000)
        for i in self.l:
            self.position_queue.put(i)
        #     # j = random.randint(22300, 330000)
        self.position_queue.put(i)#,j])
        print("Real function timing:", (datetime.datetime.now() - start).total_seconds())
        sleep(0.02)
# #
# #
#
# duration = 10

# class SendPositionsProcess(Process):
#     def __init__(self):
#         super().__init__()
#         self.position_queue = Queue()
#
#     def run(self):
#         cam = SpinnakerCamera()
#         cam.open_camera()
#         cam.set("exposure", 30)
#         start = datetime.datetime.now()
#         grab =[]
#         startshow =[]
#         blobident =[]
#
#         while True:
#             start_grabbing = datetime.datetime.now()
#             im = cam.read()
#             grab.append((datetime.datetime.now() - start_grabbing).total_seconds())
#             if im is not None:
#                 start_showing = datetime.datetime.now()
#                 # print("shape: {}".format(image_converted.shape))
#                 cv2.imshow("img", im)
#                 cv2.waitKey(1)
#                 startshow.append((datetime.datetime.now() - start_showing).total_seconds())
#
#
#                 # identify dot
#                 start_blob = datetime.datetime.now()
#                 idxs = np.unravel_index(np.nanargmin(im), im.shape)
#                 e = (np.float(idxs[1]), np.float(idxs[0]))
#                 # print(kps)
#                 blobident.append((datetime.datetime.now() - start_blob).total_seconds())
#
#                 point_x = e[0]
#                 point_y = e[1]
#
#                 # i = random.randint(1, 4400000)
#                 self.position_queue.put((point_x, point_y))
#                 # comp.append((datetime.datetime.now() - start).total_seconds())
#
#             if (datetime.datetime.now() - start).total_seconds() > duration:
#                 dd.io.save("image_aquisition.h5", pd.DataFrame(dict(grabbing_img=grab,
#                                                                   showing_img=startshow,
#                                                                   blob_det=blobident)))
#                 break



class ReceiverProcess(Process):
    def __init__(self, position_queue):
        super().__init__()
        self.position_queue = position_queue

    # def run(self):
    #     prev_event_time = datetime.datetime.now()
    #     start = datetime.datetime.now()
    #     grabbing_queue =[]
    #     grabbing_pos =[]
    #     motorposition = []
    #     motti1 = Motor(1, scale=0)
    #     motti1.open()
    #
    #     while True:
    #         try:
    #             pos = self.position_queue.get(timeout=1)
    #             grabbing_queue.append((datetime.datetime.now() - prev_event_time).total_seconds())
    #             prev_event_time = datetime.datetime.now()
    #             # print("Retrieved position x : {}".format(pos[0]))
    #             # print("Retrieved position y : {}".format(pos[1]))
    #
    #             start_motor_grab = datetime.datetime.now()
    #             motorpos = motti1.get_position()
    #             motorposition.append(motorpos)
    #             grabbing_pos.append((datetime.datetime.now()- start_motor_grab).total_seconds())
    #
    #         except Empty:
    #             pass
    #
    #         if (datetime.datetime.now() - start).total_seconds() > duration:
    #             # dd.io.save("stage_movement.h5", pd.DataFrame(dict(grabbing_queue=grabbing_queue,
    #             #                                                   grabbing_motor_pos=grabbing_pos,
    #             #                                                   motorpos=motorposition)))
    #             break
    #     motti1.close()

    def run(self):
        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()
        mottione = Motor(1, scale= 0)
        mottione.open()
        mottione.movesimple(50)
        sleep (0.2)

        while True:
            try:
                move_to = self.position_queue.get(timeout=1)
                prev_event_time = datetime.datetime.now()
                print("Retrieved position x0 : {}".format(move_to))

                pos_motor = mottione.get_position()
                print("Pos before moving: {}".format(pos_motor))

                mottione.movesimple(move_to)
                print ("motor moving")
                sleep (0.2)
                print ("time since last event: ",(datetime.datetime.now() - prev_event_time).total_seconds())

    #             # mottione.movethatthing(move_to)
    #
    #             # while not abs(pos_motor - move_to) <= 100:
    #             #     mottione.movesimple(move_to)
    #             #     print("Current pos {}".format(pos_motor) + " moving to {}".format(move_to))
    #             #     pos_motor = mottione.get_position()
    #             #     print ("time since last event: ",(datetime.datetime.now() - prev_event_time).total_seconds())
    #
    #             # newpos = (move_to-100)
    #             # while not pos_motor == newpos:
    #             #     mottione.movesimple(newpos)
    #             #     print("Current pos {}".format(pos_motor) + " moving to {}".format(move_to))
    #             #     pos_motor = mottione.get_position()
    #             #     print ("time since last event: ",(datetime.datetime.now() - prev_event_time).total_seconds())
    #
            except Empty:
                pass
    #
            if (datetime.datetime.now() - start).total_seconds() >20:
                last_pos = mottione.get_position()
                print ("last motor pos: {}".format(last_pos))
                mottione.close()
                time = (datetime.datetime.now() - start).total_seconds()
                print("time total {}".format(time))
                #
                # dd.io.save("stage_movement.h5", pd.DataFrame(dict(grabbing_queue=grabbing_queue,
                #                                                   grabbing_motor_pos=grabbing_pos,
                #                                                   motorpos=motorposition)))
                break

################################


if __name__ == '__main__':

    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()
    source.join()
    receiver.join()