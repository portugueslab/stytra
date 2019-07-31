"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

import numpy as np
from numba import vectorize, uint8, float32
from lightparam import Param
from stytra.tracking.pipelines import ImageToImageNode, NodeOutput


class Prefilter(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="filtering", **kwargs)
        self.diagnostic_image_options = ["filtered"]

    def _process(
        self,
        im,
        image_scale: Param(0.5, (0.05, 1.0)),
        filter_size: Param(2, (0, 15)),
        color_invert: Param(True),
        clip: Param(140, (0, 255)),
        **extraparams
    ):
        """ Optionally resizes, smooths and inverts the image

        :param im:
        :param state:
        :param filter_size:
        :param image_scale:
        :param color_invert:
        :return:
        """
        if image_scale != 1:
            im = cv2.resize(
                im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
            )
        if filter_size > 0:
            im = cv2.boxFilter(im, -1, (filter_size, filter_size))
        if color_invert:
            im = 255 - im
        if clip > 0:
            im = np.maximum(im, clip) - clip

        if self.set_diagnostic == "filtered":
            self.diagnostic_image = im

        return NodeOutput([], im)


@vectorize([uint8(float32, uint8)])
def negdif(xf, y):
    """

    Parameters
    ----------
    x :

    y :


    Returns
    -------

    """
    x = np.uint8(xf)
    if y < x:
        return x - y
    else:
        return 0


@vectorize([uint8(float32, uint8)])
def absdif(xf, y):
    """

    Parameters
    ----------
    x :

    y :


    Returns
    -------

    """
    x = np.uint8(xf)
    if x > y:
        return x - y
    else:
        return y - x


class BackgroundSubtractor(ImageToImageNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="bgsub", **kwargs)
        self.background_image = None
        self.i = 0

    def reset(self):
        self.background_image = None

    def _process(
        self, im, learning_rate: Param(0.04, (0.0, 1.0)),
        learn_every: Param(400, (1, 10000)),
        only_darker: Param(True)
    ):
        messages = []
        if self.background_image is None:
            self.background_image = im.astype(np.float32)
            messages.append("I:New backgorund image set")
        elif self.i == 0:
            self.background_image[:, :] = im.astype(np.float32) * np.float32(
                learning_rate
            ) + self.background_image * np.float32(1 - learning_rate)

        self.i = (self.i + 1) % learn_every

        if only_darker:
            return NodeOutput(messages, negdif(self.background_image, im))
        else:
            return NodeOutput(messages, absdif(self.background_image, im))
