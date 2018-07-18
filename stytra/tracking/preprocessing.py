"""
    Preprocessing functions, take the current image, some state (optional,
    used for backgorund subtraction) and parameters and return the processed image

"""
import cv2

from stytra.tracking import ParametrizedImageproc
import numpy as np


class PreprocMethod(ParametrizedImageproc):
    def __init__(self):
        super().__init__()
        self.add_params(display_processed=False)


class Prefilter(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            filter_size=0,
            image_scale=dict(type="float", value=0.5, limits=(0.01, 1.0)),
            color_invert=False,
        )

    # We have to rely on class methods here, as Parametrized objects can only
    # live in the main process
    @classmethod
    def process(
        cls,
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
        self.collected_images = np.empty((n_mean,) + im.shape, im.dtype)
        self.i = 0
        self.n_collected = 0
        self.n_mean = n_mean

    def update(self, im):
        self.collected_images[self.i, :, :] = im
        self.i = (self.i + 1) % self.n_mean
        self.n_collected = min(self.n_collected + 1, self.n_mean)

    def subtract(self, im):
        return cv2.absdiff(im, np.mean(self.collected_images[: self.n_collected, :, :]))

    def reset(self):
        self.n_collected = 0


class BackgorundSubtractor(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            n_mean=100, image_scale=dict(type="float", value=1, limits=(0.01, 1.0))
        )
        self.collected_images = None

    @classmethod
    def process(cls, im, state=None, n_mean=100, image_scale=1, **extraparams):
        if image_scale != 1:
            im = cv2.resize(
                im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
            )
        if state is None or state.n_mean != n_mean:
            state = BgSubState(im, n_mean)
        state.update(im)
        return state.subtract(im), state


class CVSubtractorState:
    def __init__(self, method, threshold):
        self.method = method
        self.threshold = threshold
        if method == "knn":
            self.subtractor = cv2.createBackgroundSubtractorKNN(
                dist2Threshhold=threshold, detectShadows=False
            )
        else:
            self.subtractor = cv2.createBackgroundSubtractorMOG2(
                varThreshold=threshold, detectShadows=False
            )

    def update(self, im):
        return self.subtractor.apply(im)


class CV2BgSub(PreprocMethod):
    def __init__(self):
        super().__init__()
        self.add_params(
            method=dict(type="list", value="mog2", values=["knn", "mog2"]),
            threshold=128,
        )
        self.collected_images = None

    @classmethod
    def process(
        cls, im, state=None, method="mog2", image_scale=1, threshold=128, **extraparams
    ):
        if state is None or state.method != method or state.threshold != threshold:
            state = CVSubtractorState(method, threshold)
        return state.update(im), state
