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
import deepdish as dd
import pandas as pd

#########################################
import PyQt5
from PyQt5 import QtCore, QtGui
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import random

app = QtGui.QApplication([])
p = pg.plot()
curve = p.plot()
data = [0]

def updater():

    data.append(random.random())
    curve.setData(data) #xdata is not necessary


timer = QtCore.QTimer()
timer.timeout.connect(updater)
timer.start(0)

if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


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
        grab =[]
        startshow =[]
        blobident =  []

        while True:
            start_grabbing = datetime.datetime.now()
            image_converted = cam.read()
            grab.append((datetime.datetime.now() - start_grabbing).total_seconds())
            if image_converted is not None:
                start_showing = datetime.datetime.now()
                # print("shape: {}".format(image_converted.shape))
                cv2.imshow("img", image_converted)
                cv2.waitKey(1)
                startshow.append((datetime.datetime.now() - start_showing).total_seconds())


                # identify dot
                start_blob = datetime.datetime.now()
                blobdet = cv2.SimpleBlobDetector_create()
                keypoints = blobdet.detect(image_converted)
                kps = np.array([k.pt for k in keypoints])
                # print(kps)
                blobident.append((datetime.datetime.now() - start_blob).total_seconds())

                point_x = int(kps[0][0])
                point_y = int(kps[0][1])

                # i = random.randint(1, 4400000)
                self.position_queue.put((point_x, point_y))
                # comp.append((datetime.datetime.now() - start).total_seconds())

            if (datetime.datetime.now() - start).total_seconds() > duration:
                dd.io.save("image_aquisition.h5", pd.DataFrame(dict(grabbing_img=grab,
                                                                  showing_img=startshow,
                                                                  blob_det=blobident)))
                break

class ReceiverProcess(Process):
    def __init__(self, position_queue):
        super().__init__()
        self.position_queue = position_queue

    def run(self):
        prev_event_time = datetime.datetime.now()
        start = datetime.datetime.now()
        grabbing_queue =[]
        grabbing_pos =[]
        motorposition = []
        motti1 = Motor(1)
        motti1.open()

        while True:
            try:
                pos = self.position_queue.get(timeout=1)
                grabbing_queue.append((datetime.datetime.now() - prev_event_time).total_seconds())
                prev_event_time = datetime.datetime.now()
                # print("Retrieved position x : {}".format(pos[0]))
                # print("Retrieved position y : {}".format(pos[1]))

                start_motor_grab = datetime.datetime.now()
                motorpos = motti1.get_position()
                motorposition.append(motorpos)
                grabbing_pos.append((datetime.datetime.now()- start_motor_grab).total_seconds())

            except Empty:
                pass

            if (datetime.datetime.now() - start).total_seconds() > duration:
                dd.io.save("stage_movement.h5", pd.DataFrame(dict(grabbing_queue=grabbing_queue,
                                                                  grabbing_motor_pos=grabbing_pos,
                                                                  motorpos = motorposition)))
                break
        motti1.close()

################################

if __name__ == '__main__':

    source = SendPositionsProcess()
    receiver = ReceiverProcess(source.position_queue)
    source.start()
    receiver.start()
    source.join()
    receiver.join()