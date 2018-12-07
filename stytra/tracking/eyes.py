"""
    Authors: Andreas Kist, Luigi Petrucco
"""

import numpy as np
from skimage.filters import threshold_local
import cv2
from lightparam import Parametrized, Param


class EyeTrackingMethod:
    """General eyes tracking method."""

    name = "eyes"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.params = Parametrized(name="tracking/eyes", params=self.detect)

        headers = []
        for i in range(2):
            headers.extend(
                [
                    "pos_x_e{}".format(i),
                    "pos_y_e{}".format(i),
                    "dim_x_e{}".format(i),
                    "dim_y_e{}".format(i),
                    "th_e{}".format(i),
                ]
            )

        self.monitored_headers = ["th_e0", "th_e1"]
        self.accumulator_headers = headers
        self.data_log_name = "behavior_eyes_log"

    def detect(
        self,
        im,
        wnd_pos: Param((0, 0), gui=False),
        threshold: Param(100, limits=(1, 254)),
        wnd_dim: Param((100, 100), gui=False),
        **extraparams
    ):
        """

        Parameters
        ----------
        im :
            image (numpy array);
        win_pos :
            position of the window on the eyes (x, y);
        win_dim :
            dimension of the window on the eyes (w, h);
        threshold :
            threshold for ellipse fitting (int).

        Returns
        -------

        """
        message = ""
        PAD = 0

        cropped = _pad(
            im[
                wnd_pos[1] : wnd_pos[1] + wnd_dim[1],
                wnd_pos[0] : wnd_pos[0] + wnd_dim[0],
            ].copy(),
            padding=PAD,
            val=255,
        )

        # try:
        e = _fit_ellipse(cropped)

        if e is False:
            e = (np.nan,) * 10
            message = "E: eyes not detected!"
        else:
            e = (
                e[0][0][::-1]
                + e[0][1][::-1]
                + (-e[0][2],)
                + e[1][0][::-1]
                + e[1][1][::-1]
                + (-e[1][2],)
            )
        return message, np.array(e)


def _pad(im, padding=0, val=0):
    """Lazy function for padding image

    Parameters
    ----------
    im :

    val :
        return: (Default value = 0)
    padding :
         (Default value = 0)

    Returns
    -------

    """
    padded = np.lib.pad(
        im,
        ((padding, padding), (padding, padding)),
        mode="constant",
        constant_values=((val, val), (val, val)),
    )
    return padded


def _local_thresholding(im, padding=2, block_size=17, offset=70):
    """Local thresholding

    Parameters
    ----------
    im :
        The camera frame with the eyes
    padding :
        padding of the camera frame (Default value = 2)
    block_size :
        param offset: (Default value = 17)
    offset :
         (Default value = 70)

    Returns
    -------
    type
        thresholded image

    """
    padded = _pad(im, padding, im.min())
    return padded > threshold_local(padded, block_size=block_size, offset=offset)


def _fit_ellipse(thresholded_image):
    """Finds contours and fits an ellipse to thresholded image

    Parameters
    ----------
    thresholded_image :
        Binary image containing two eyes

    Returns
    -------
    type
        When eyes were found, the two ellipses, otherwise False

    """
    _, contours, hierarchy = cv2.findContours(
        thresholded_image.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contours) >= 2:

        # Get the two largest ellipses (i.e. the eyes, not any dirt)
        contours = sorted(contours, key=lambda c: c.shape[0], reverse=True)[:2]
        # Sort them that first ellipse is always the left eye (in the image)
        contours = sorted(contours, key=np.max)

        # Fit the ellipses for the two eyes
        if len(contours[0]) > 4 and len(contours[1]) > 4:
            e = [cv2.fitEllipse(contours[i]) for i in range(2)]
            return e
        else:
            return False

    else:
        # Not at least two eyes + maybe dirt found...
        return False
