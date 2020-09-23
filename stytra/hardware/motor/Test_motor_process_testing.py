from multiprocessing import Process, Queue, Event
from queue import Empty
from time import sleep
import datetime
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.motor.motor_calibrator import MotorCalibrator
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
import random
import cv2
import numpy as np
import pandas as pd
import deepdish as dd
import matplotlib.pyplot as plt

duration = 10

class SendPositionsProcess(Process):
    def __init__(self):
        super().__init__()
        self.position_queue = Queue()

    def run(self):
        cam = SpinnakerCamera()
        cam.open_camera()
        cam.set("exposure", 5)

        while True:
            im = cam.read()
            cv2.imshow("img", im)
            cv2.waitKey(5)
            self.position_queue.put(im)




class ReceiverProcess(Process):
    def __init__(self, dot_position_queue, finished_event):
        super().__init__()
        self.position_queue = dot_position_queue
        self.finished_event = finished_event
        self.thres = 5

    # def run(self):
    #     start = datetime.datetime.now()
    #     motor_y = Motor(1, scale=1818)
    #     motor_x = Motor(2, scale=1250)
    #     cali = MotorCalibrator(motor_x, motor_y)
    #     motor_y.open()
    #     motor_x.open()
    #     center_y = 270
    #     center_x = 360
    #
    #     while not self.finished_event.is_set():
    #         try:
    #             pos = self.position_queue.get(timeout=1)
    #         except Empty:
    #             pass
    #
    #         if pos is not None:
    #             cali.background_sub(pos[0], pos[1], pos[2])
    #
    #             pos_x = motor_x.get_position()
    #             pos_y = motor_y.get_position()
    #             print ("motorpos", pos_x, pos_y)
    #
    #             try:
    #                 distance_x = center_x - pos[0]
    #                 distance_y = center_y - pos[1]
    #
    #                 if distance_x ** 2 + distance_y ** 2 > self.thres ** 2:
    #                     print("Moving")
    #                     motor_x.move_relative(distance_x)
    #                     motor_y.move_relative(distance_y)
    #                     print(distance_x, distance_y)
    #
    #             except (ValueError, TypeError, IndexError):
    #                 pass
    #
    #         if (datetime.datetime.now() - start).total_seconds() > duration:
    #             motor_x.close()
    #             motor_y.close()
    #             break

    def run(self):
        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()
        mottione = Motor(1, scale=0)
        mottione.open()
        mottitwo = Motor(2, scale=0)
        mottitwo.open()
        moto = []
        time = []
        distances = []
        while True:
            #         oldpos = 0
            try:
                #
                #             # newpos =self.position_queue.get(timeout=0)
                #             # print("Retrieved position newpos: {}".format(newpos))
                #             # mottipos = mottione.get_position()
                #             # print("motor position before loop:", mottipos)
                #             #
                #             # if newpos != oldpos:
                #             #     mottione.stopprof()
                #             #     # mottione.stopimm()
                #             #     mottione.movesimple(position=newpos)
                #             #     mottipos = mottione.get_position()
                #             #     print("motor position after move:", mottipos)
                #             #     sleep(0.3)
                #             #     oldpos = newpos
                #             #     print ("oldpos",oldpos)
                #             #
                #
                im = self.position_queue.get(timeout=0)

                arena = (1200, 1200)
                background_0 = np.zeros(arena)
                motor_posx = mottione.get_position()

                positions_h = [1900000, 2100000, 2300000]
                positions_w = [1900000, 2100000, 2300000]
                # con = motor_posx / (arena[0] / 2)
                con = motor_posx / (arena[0] / 2)
                print(con)

                for pos in positions_h:
                    for posi in positions_w:
                        # print("y:", pos, ",x:", posi)
                        mottitwo.movethatthing(pos)
                        mottione.movethatthing(posi)

                        motor_posx = mottione.get_position()
                        motor_posy = mottitwo.get_position()

                        motor_x = motor_posx / con
                        motor_y = motor_posy / con
                        # print ("motor pos orginal", self.motor_posx, self.motor_posy)
                        # print ("motor after con", motor_x, motor_y)

                        mx = int(motor_x - im.shape[0] / 2)
                        mxx = int(motor_x + im.shape[0] / 2)
                        my = int(motor_y - im.shape[1] / 2)
                        myy = int(motor_y + im.shape[1] / 2)
                        print(mx, mxx, my, myy)
                        background_0[mx:mxx, my:myy] = im

                # prev_event_time = datetime.datetime.now()
                # print("Retrieved position x: {}".format(move_to))
                #
                # mottione.movesimple(move_to)
                #
                # motor_pos = mottione.get_position()
                #
                # while motor_pos != move_to:
                #     dist = (move_to - motor_pos)
                #     print("Current pos {}".format(motor_pos) + " moving to {}".format(move_to))
                #     print("distance: ", dist)
                #     motor_pos = mottione.get_position()
                #     moto.append(motor_pos)
                #     distances.append(dist)
                #     time.append((datetime.datetime.now() - prev_event_time).total_seconds())
                #     sleep(0.001)

                # print("coords", moto)
                # print("time", time)
                # print("dist", distances)
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

            if (datetime.datetime.now() - start).total_seconds() > 3:
                last_pos = mottione.get_position()
                print("last motor pos: {}".format(last_pos))
                mottione.close()
                time = (datetime.datetime.now() - start).total_seconds()
                print("time total {}".format(time))
                cv2.imwrite("test.jpg", background_0)

                #
                # dd.io.save("stage_movement.h5", pd.DataFrame(dict(grabbing_queue=grabbing_queue,
                #                                                   grabbing_motor_pos=grabbing_pos,
                #                                                   motorpos=motorposition)))
                break


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
