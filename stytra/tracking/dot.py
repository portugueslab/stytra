
import numpy as np
from skimage.filters import threshold_local
import cv2
from lightparam import Parametrized, Param
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera
from stytra.hardware.motor.stageAPI import Motor
from stytra.hardware.motor.motor_calibrator import MotorCalibrator
from time import sleep
from scipy.spatial import distance


class DotTrackingMethod(ImageToDataNode):
    """General dot tracking method."""

    name = "dot"

    def __init__(self, motor1, motor2, motorcalibrator, *args, **kwargs):

        super().__init__(*args,  name="dot_tracking", **kwargs)

        self.motti1 = motor1
        self.motti2 = motor2
        self.mc = motorcalibrator

        self._output_type = namedtuple("xy", ["pos_x_dot", "pos_y_dot"])

        self.conversion_x, self.conversion_y = self.mc.calibrate_motor()

        self.move_to_conx = self.motti2.get_position()
        self.move_to_cony = self.motti1.get_position()

    def _process(self): #,im):
        #TODO change camera aquisition somehow
        self.cam = SpinnakerCamera()
        self.cam.open_camera()
        self.cam.set("exposure", 12)

        #grabbing image
        image_converted = self.cam.read()
        cv2.imshow("img", image_converted)
        cv2.waitKey(10)

        # identify dot
        blobdet = cv2.SimpleBlobDetector_create()
        keypoints = blobdet.detect(image_converted)
        kps = np.array([k.pt for k in keypoints])

        self.center_y = 270  #TODO  change hardcoding and get info from camera directly
        self.center_x = 360

        self.point_x = int(kps[0][0])  # change: what will happen with more than one dot?
        self.point_y = int(kps[0][1])

        # Calculations for motor moves
        self.distance_x = int(self.center_x - self.point_x)
        self.distance_y = int(self.center_y - self.point_y)
        print("kps: {}".format(kps))

        connx = int(self.distance_x * self.conversion_x)
        conny = int(self.distance_y * self.conversion_y)

        pos_x = self.motti2.get_position()
        pos_y = self.motti1.get_position()
        print("stage at x,y:", pos_x, pos_y)


        conx = pos_x + int(connx * 0.95)
        self.move_to_conx = conx
        dstx = distance.euclidean(pos_x, self.move_to_conx)

        if dstx > 10000:
            self.motti2.movesimple(conx)

        
        cony = pos_y + int(conny * 0.95)
        self.move_to_cony = cony
        dsty = distance.euclidean(pos_y, self.move_to_cony)
        print (dsty)
        if dsty > 10000:
            self.motti1.movesimple(cony)

        # e = (conx, cony)
        e = (self.move_to_conx, self.move_to_cony)

        self.cam.cam.EndAcquisition()

        return NodeOutput(
            ["dot x,y", ],
            self._output_type(*e)
        )


if __name__ == "__main__":
    motor1 = Motor (1)
    motor2 = Motor (2)
    motor1.open()
    motor2.open()
    motorcalib = MotorCalibrator(motor1, motor2) #TODO external calibration somewhere else?

    dottrack = DotTrackingMethod(motor1, motor2, motorcalib)

    while True:
        node_output = dottrack._process()
        print (node_output)


    dottrack.cam.EndAcquisition()

    motor1.close()
    motor2.close()