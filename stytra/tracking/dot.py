import numpy as np
from skimage.filters import threshold_local
import cv2
from lightparam import Parametrized, Param
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple
from stytra.hardware.video.cameras.spinnaker import SpinnakerCamera

# from stytra.hardware.motor.stageAPI import Motor
# from stytra.hardware.motor.motor_calibrator import MotorCalibrator
from time import sleep
from scipy.spatial import distance


class DotTrackingMethod(ImageToDataNode):
    """General dot tracking method."""

    name = "dot"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, name="dot_tracking", **kwargs)

        self._output_type = namedtuple("xy", ["x", "y"])

    def _process(self, im):
        # identify dot
        try:
            msg = ""
            # self.center_y = 270  # TODO  change hardcoding and get info from camera directly
            # self.center_x = 360
            idxs = np.unravel_index(np.nanargmin(im), im.shape)
            e = (np.float(idxs[1]), np.float(idxs[0]))
        except (TypeError, IndexError):
            msg = "E:No dot found"
            e = (None, None)

        # Calculations for motor moves
        # self.distance_x = int(self.center_x - self.point_x)
        # self.distance_y = int(self.center_y - self.point_y)
        # # print("kps: {}".format(kps))
        #
        # connx = int(self.distance_x * self.conversion_x)
        # conny = int(self.distance_y * self.conversion_y)
        #
        # pos_x = self.motti2.get_position()
        # pos_y = self.motti1.get_position()
        # print("stage at x,y:", pos_x, pos_y)

        #
        # conx = pos_x + int(connx * 0.95)
        # self.move_to_conx = conx
        # dstx = distance.euclidean(pos_x, self.move_to_conx)
        #
        # if dstx > 10000:
        #     self.motti2.movesimple(conx)
        #
        #
        # cony = pos_y + int(conny * 0.95)
        # self.move_to_cony = cony
        # dsty = distance.euclidean(pos_y, self.move_to_cony)
        # print (dsty)
        # if dsty > 10000:
        #     self.motti1.movesimple(cony)
        #
        # #
        # e = (self.move_to_conx, self.move_to_cony)
        #
        # self.cam.cam.EndAcquisition()

        return NodeOutput([msg], self._output_type(*e))


if __name__ == "__main__":
    motor1 = Motor(1)
    motor2 = Motor(2)
    motor1.open()
    motor2.open()
    motorcalib = MotorCalibrator(
        motor1, motor2
    )  # TODO external calibration somewhere else?

    dottrack = DotTrackingMethod(motor1, motor2, motorcalib)

    while True:
        node_output = dottrack._process()
        print(node_output)

    dottrack.cam.EndAcquisition()

    motor1.close()
    motor2.close()
