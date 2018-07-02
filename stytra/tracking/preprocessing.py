"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

from stytra.tracking import ParametrizedImageproc
import numpy as np


class Prefilter(ParametrizedImageproc):

    def __init__(self):
        super().__init__()
        self.add_params(filter_size=0, image_scale=0.5, color_invert=False)

    # We have to rely on class methods here, as Parametrized objects can only
    # live in the main process
    @classmethod
    def process(
        self,
        im,
        state=None,
        image_scale=1,
        filter_size=0,
        color_invert=False,
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

        return im, None


class BgSubState:
    """  A class which implements simple backgorund sutraction by keeping a
    the background model in a circular buffer

    """

    def __init__(self, im, n_mean):
        self.collected_images = np.array((n_mean,) + im.shape, im.dtype)
        self.i = 0
        self.n_collected = 0
        self.n_mean = n_mean

    def update(self, im):
        self.collected_images[self.i, :, :] = im
        self.i = (self.i + 1) % self.n_mean
        self.collected = min(self.collected + 1, self.n_mean)

    def subtract(self, im):
        return cv2.absdiff(im, np.mean(self.collected_images[: self.collected, :, :]))

    def reset(self):
        self.n_collected = 0


class BackgorundSubtractor(ParametrizedImageproc):
    def __init__(self):
        super().__init__()
        self.add_params(n_mean=100)
        self.collected_images = None

    def subtract_background_simple(self, im, state=None, n_mean=1, **extraparams):
        if state is None:
            state = BgSubState(im, n_mean)
        state.update(im)
        return state.subtract(im), state
