import cv2
import numpy as np

from stytra.tracking.eyes import EyeTrackingMethod
from stytra.tracking.tail import AnglesTrackingMethod, TailTrackingMethod
from itertools import chain


class TailEyesTrackingMethod(TailTrackingMethod, EyeTrackingMethod):
    name = "eyes_tail"

    def __init__(self):
        super().__init__()
        headers = ["tail_sum"] + [
            "theta_{:02}".format(i) for i in range(self.params["n_output_segments"])
        ]
        [
            headers.extend(
                [
                    "pos_x_e{}".format(i),
                    "pos_y_e{}".format(i),
                    "dim_x_e{}".format(i),
                    "dim_y_e{}".format(i),
                    "th_e{}".format(i),
                ]
            )
            for i in range(2)
        ]
        self.monitored_headers = ["tail_sum", "th_e0", "th_e1"]
        self.accumulator_headers = headers
        self.data_log_name = "behavior_tail_eyes_log"
        self.method_chain = [AnglesTrackingMethod(), EyeTrackingMethod()]

    def detect(self, im, **kwargs):
        return tuple(
            chain.from_iterable(met.detect(im, **kwargs) for met in self.method_chain)
        )
