"""
    Authors: Andreas Kist, Luigi Petrucco
"""

import numpy as np
from skimage.filters import threshold_local
import cv2
from lightparam import Parametrized, Param
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple


class EyeTrackingMethod(ImageToDataNode):
    """General eyes tracking method."""

    name = "eyes"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="eyes_tracking", **kwargs)

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
        self._output_type = namedtuple("t", headers)

        self.monitored_headers = ["th_e0", "th_e1"]

        self.data_log_name = "eye_track"

        self.diagnostic_image_options = ["thresholded"]

    def _process(
        self,
        im,
        wnd_pos: Param((129, 20), gui=False),
        threshold: Param(56, limits=(1, 254)),
        wnd_dim: Param((14, 22), gui=False),
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
            (
                im[
                    wnd_pos[1] : wnd_pos[1] + wnd_dim[1],
                    wnd_pos[0] : wnd_pos[0] + wnd_dim[0],
                ]
                < threshold
            )
            .view(dtype=np.uint8)
            .copy(),
            padding=PAD,
            val=255,
        )

        # try:
        e = _fit_ellipse(cropped)

        if self.set_diagnostic == "thresholded":
            self.diagnostic_image = (im < threshold).view(dtype=np.uint8)

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
        return NodeOutput([message], self._output_type(*e))


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
    cont_ret = cv2.findContours(
        thresholded_image.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    # API change, in OpenCV 4 there are 2 values unlike OpenCV3
    if len(cont_ret) == 3:
        _, contours, hierarchy = cont_ret
    else:
        contours, hierarchy = cont_ret

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
