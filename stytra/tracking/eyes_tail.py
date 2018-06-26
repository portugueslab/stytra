import cv2
import numpy as np
from numba import vectorize, uint8, jit

from stytra.tracking.eyes import _pad, _fit_ellipse
from stytra.tracking.tail import _tail_trace_core_ls

# TODO it would be better to avoid this function and sequentially apply its
# two parts


def trace_tail_eyes(
    im,
    wnd_pos=(0, 0),
    wnd_dim=(10, 10),
    threshold=65,
    tail_start=(0, 0),
    n_segments=7,
    tail_length=(1, 1),
    filter_size=0,
    color_invert=False,
    image_scale=1,
):
    """Tail tracing based on min (or max) detection on arches. Wraps
    _tail_trace_core_ls. Speed testing: 20 us for a 514x640 image without
    smoothing, 300 us with smoothing.

    Parameters
    ----------
    img :
        input image
    tail_start :
        tail starting point (x, y) (Default value = (0)
    tail_length :
        tail length (Default value = (1)
    n_segments :
        number of segments (Default value = 7)
    filter_size :
        Box for smoothing the image (Default value = 0)
    color_invert :
        True for inverting image colors (Default value = False)
    im :

    0) :

    1) :

    image_scale :
         (Default value = 1)

    Returns
    -------

    """

    start_x = tail_start[1]  # TODO remove
    start_y = tail_start[0]
    tail_length_x = tail_length[1]
    tail_length_y = tail_length[0]

    # Image preprocessing. Resize if required:
    if image_scale != 1:
        im = cv2.resize(
            im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA
        )

    PAD = 0

    cropped = _pad(
        im[
            wnd_pos[0] : wnd_pos[0] + wnd_dim[0], wnd_pos[1] : wnd_pos[1] + wnd_dim[1]
        ].copy(),
        padding=PAD,
        val=255,
    )

    # Filter if required:
    if filter_size > 0:
        im = cv2.boxFilter(im, -1, (filter_size, filter_size))

    # Calculate tail length:
    length_tail = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2) * image_scale

    # Initial displacements in x and y:
    disp_x = tail_length_x * image_scale / n_segments
    disp_y = tail_length_y * image_scale / n_segments

    start_x *= image_scale
    start_y *= image_scale

    # Use jitted function for the actual calculation:
    angle_list = _tail_trace_core_ls(
        im, start_x, start_y, disp_x, disp_y, n_segments, length_tail, color_invert
    )

    thresholded = (cropped < threshold).astype(np.uint8)

    # try:
    e = _fit_ellipse(thresholded)
    if e is False:
        print("I don't find eyes here...")
        e = (np.nan,) * 10
    else:
        e = e[0][0] + e[0][1] + (e[0][2],) + e[1][0] + e[1][1] + (e[1][2],)

    return np.concatenate([angle_list, np.array(e)])
