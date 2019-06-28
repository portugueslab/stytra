
import numpy as np
from skimage.filters import threshold_local
import cv2
from lightparam import Parametrized, Param
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple


class DotTrackingMethod(ImageToDataNode):
    """General dot tracking method."""

    name = "dot"

    def __init__(self, *args, **kwargs):
        super().__init__(*args,  name="dot_tracking", **kwargs)

        headers = []
        for i in range(2):
            headers.extend(
                [
                    "pos_x_dot{}".format(i),
                    "pos_y_dot{}".format(i)
                ]
            )
        self._output_type = namedtuple("xy", headers)
        ]

    def _process(self,im):

        image_converted = self.cam.read()
        cv2.imshow("img", image_converted)
        cv2.waitKey(30)

        # identify dot
        blobdet = cv2.SimpleBlobDetector_create()
        keypoints = blobdet.detect(image_converted)
        kps = np.array([k.pt for k in keypoints])

        self.center_y = 270  #TODO maybe change hardcoding and get info from camera directly
        self.center_x = 360

        self.point_x = int(kps[0][0])  # change: what will happen with more than one dot?
        self.point_y = int(kps[0][1])

        self.distance_x = int(self.center_x - self.point_x)
        self.distance_y = int(self.center_y - self.point_y)
        print("kps: {}".format(kps))

        distx = int(center_x - x)
        disty = int(center_y - y)

        connx = int(distx * 1538)  # TODO get from calibrator
        conny = int(disty * 1538)

        pos_x = self.motti2.get_position()
        pos_y = self.motti1.get_position()
        print("stage at x,y:", pos_x, pos_y)

        con = pos_x + connx
        mottitwo.movesimple(con)

        cony = pos_y + conny
        mottione.movesimple(cony)

        if e is False:
            e = (np.nan,) * 10
            message = "E: eyes not detected!"
        else:
            e = (xy)
            )
        return NodeOutput(
            [message, ],
            self._output_type(*e)
        )
