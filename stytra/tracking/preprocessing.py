"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

import numpy as np
from numba import vectorize, uint8, float32
from lightparam import Parametrized, Param


class Prefilter:
    def __init__(self):
        super().__init__()
        self.params = Parametrized(name="tracking/prefiltering", params=self.process)

    # We have to rely on class methods here, as Parametrized objects can only
    # live in the main process
    def process(
        self,
        im,
        image_scale: Param(1.0, (0.05, 1.0)),
        filter_size: Param(0, (0, 15)),
        color_invert: Param(False),
        clip: Param(0, (0, 255)),
        display_processed: Param("raw", ["raw", "filtered"]) = "raw",
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

        return im


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


class BackgorundSubtractor:
    def __init__(self):
        super().__init__()
        self.background_image = None
        self.i = 0

    def process(
        self, im, learning_rate=0.001, learn_every=1, reset=False, **extraparams
    ):
        if reset:
            self.background_image = None

        if self.background_image is None:
            self.background_image = im.astype(np.float32)
        elif self.i == 0:
            self.background_image[:, :] = im.astype(np.float32) * np.float32(
                learning_rate
            ) + self.background_image * np.float32(1 - learning_rate)

        self.i = (self.i + 1) % learn_every

        return negdif(self.background_image, im)
