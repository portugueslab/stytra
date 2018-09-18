"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

from stytra.tracking import ParametrizedImageproc
import numpy as np
from numba import vectorize, uint8, float32


class PreprocMethod(ParametrizedImageproc):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_params(display_processed=False)


class Prefilter(PreprocMethod):
    def __init__(self):
        super().__init__(name="tracking_prefiltering")
        self.add_params(
            filter_size=0,
            image_scale=dict(type="float", value=1.0, limits=(0.01, 1.0)),
            color_invert=False,
        )

    # We have to rely on class methods here, as Parametrized objects can only
    # live in the main process
    def process(
        self, im, image_scale=1, filter_size=0, color_invert=False, **extraparams
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


class BackgorundSubtractor(PreprocMethod):
    def __init__(self):
        super().__init__(name="tracking_bgsubtraction")
        self.add_params(
            learning_rate=dict(type="float", value=0.01, limits=(0.001, 1.0)),
            learn_every=dict(type="int", value=1, limits=(1, 1000)),
            reset=dict(type="bool", value=False),
        )
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


class CV2BgSub(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            method=dict(type="list", value="mog2", values=["knn", "mog2"]),
            threshold=128,
        )

    def process(self, im, method="mog2", image_scale=1, threshold=128, **extraparams):

        if (
            self.subtractor is None
            or self.method != method
            or self.threshold != threshold
        ):
            if method == "knn":
                self.subtractor = cv2.createBackgroundSubtractorKNN(
                    dist2Threshhold=threshold, detectShadows=False
                )
            else:
                self.subtractor = cv2.createBackgroundSubtractorMOG2(
                    varThreshold=threshold, detectShadows=False
                )
        return self.subtractor.apply(im)
