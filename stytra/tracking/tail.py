import numpy as np
from numba import jit


@jit(nopython=True)
def detect_segment(detect_angles, seglen, start, direction, image):
    """

    :param detect_angles: a list of angles at which tto evalueate the next point
    :param seglen: length of the segment
    :param start: starting point
    :param direction: angle to search around
    :param image: image containing the tail
    :return:
    """
    d_angles = direction + detect_angles

    weighted_angles = 0.0
    brightnesses = 0.0

    for i in range(detect_angles.shape[0]):
        coord = (int(start[0]+seglen*np.cos(d_angles[i])),
                 int(start[1] + seglen * np.sin(d_angles[i])))
        if ((coord[0] > 0) & (coord[0] < image.shape[1]) &
            (coord[1] > 0) & (coord[1] < image.shape[0])):
            brg = image[coord[1], coord[0]]
            weighted_angles += brg*detect_angles[i]
            brightnesses += brg

    if brightnesses == 0.0:
        return 0
    return weighted_angles/brightnesses


@jit(nopython=True)
def detect_tail(image, start_point, start_dir=0, pixlen=100, segments=5, max_segment_angle=np.pi*3/8):
    seglen = pixlen * 1.0 / segments

    detect_angles = np.linspace(-max_segment_angle, max_segment_angle, 17)
    angles = np.zeros(segments, dtype=np.float32)
    start_dir = start_dir
    last_dir = start_dir
    start_point = start_point.copy()
    for i in range(segments):
        angles[i] = detect_segment(detect_angles, seglen,
                                        start_point, last_dir, image,
                                        i / (segments + 1))
        if angles[i] == np.nan:
            break
        last_dir += angles[i]
        start_point += seglen * np.array(
            [np.cos(last_dir), np.sin(last_dir)])

    return angles


@jit(nopython=True)
def find_direction(start, image, seglen):
    n_angles = 20
    angles = np.arange(n_angles) * np.pi * 2 / n_angles

    detect_angles = angles

    weighted_vector = np.zeros(2)

    for i in range(detect_angles.shape[0]):
        coord = (int(start[0] + seglen * np.cos(detect_angles[i])),
                 int(start[1] + seglen * np.sin(detect_angles[i])))
        if ((coord[0] > 0) & (coord[0] < image.shape[1]) &
                (coord[1] > 0) & (coord[1] < image.shape[0])):
            brg = image[coord[1], coord[0]]

            weighted_vector += brg * np.array([np.cos(detect_angles[i]), np.sin(detect_angles[i])])

    return np.arctan2(weighted_vector[1], weighted_vector[0])


@jit(nopython=True)
def detect_tail_unknown_dir(image, start_point, eyes_to_tail=10, tail_length=100,
                            segments=5):
    seglen = tail_length * 1.0 / segments

    max_segment_angle = np.pi * 3 / 8
    detect_angles = np.linspace(-max_segment_angle, max_segment_angle, 17)
    angles = np.zeros(segments, dtype=np.float32)
    start_dir = find_direction(start_point, image, eyes_to_tail)

    last_dir = start_dir
    start_point += eyes_to_tail * np.array([np.cos(start_dir),
                                            np.sin(start_dir)])
    for i in range(segments):
        angles[i] = detect_segment(detect_angles, seglen,
                                    start_point, last_dir, image)
        if angles[i] == np.nan:
            break
        last_dir += angles[i]
        start_point += seglen * np.array(
            [np.cos(last_dir), np.sin(last_dir)])

    return start_dir, angles


@jit(nopython=True)
def _next_segment(fc, xm, ym, dx, dy, wind_size, next_point_dist):
    """ Find the enpoint of the next tail segment
    by calculating the moments in a look-ahead area

    :param fc: image to find tail
    :param xm: starting point x
    :param ym: starting point y
    :param dx: initial displacement x
    :param dy: initial displacement y
    :param wind_size: size of the window to estimate next tail point
    :param next_point_dist: distance to the next tail point
    :return:
    """

    # Generate square window for center of mass
    y_max, x_max = fc.shape
    xs = min(max(int(round(xm + dx - wind_size / 2)), 0), x_max)
    xe = min(max(int(round(xm + dx + wind_size / 2)), 0), x_max)
    ys = min(max(int(round(ym + dy - wind_size / 2)), 0), y_max)
    ye = min(max(int(round(ym + dy + wind_size / 2)), 0), y_max)

    # at the edge returns invalid data
    if xs == xe and ys == ye:
        return -1, -1, 0, 0, 0

    # accumulators
    acc = 0.0
    acc_x = 0.0
    acc_y = 0.0
    for x in range(xs, xe):
        for y in range(ys, ye):
            acc_x += x * fc[y, x]
            acc_y += y * fc[y, x]
            acc += fc[y, x]

    if acc == 0:
        return -1, -1, 0, 0, 0

    # center of mass relative to the starting points
    mn_y = acc_y / acc - ym
    mn_x = acc_x / acc - xm

    # normalise to segment length
    a = np.sqrt(mn_y ** 2 + mn_x ** 2) / next_point_dist

    # check center of mass validity
    if a == 0:
        return -1, -1, 0, 0, 0

    # Use normalization factor
    dx = mn_x / a
    dy = mn_y / a

    return xm + dx, ym + dy, dx, dy, acc


@jit(nopython=True, cache=True)
def angle(dx1, dy1, dx2, dy2):
    alph1 = np.arctan2(dy1, dx1)
    alph2 = np.arctan2(dy2, dx2)
    diff = alph2 - alph1
    if diff >= np.pi:
        diff -= 2*np.pi
    if diff <= -np.pi:
        diff += 2*np.pi
    return diff


def detect_tail_canny(im, **kwargs):
    import cv2
    edges = cv2.Canny(im, 100, 200)
    return detect_tail_new(edges, inverted=False, **kwargs)


@jit(nopython=True, cache=True)
def detect_tail_new(im, start_x, start_y, tail_len_x, tail_len_y, n_segments=30, window_size=30,
                    inverted=True):
    """ Finds the tail for an embedded fish, given the starting point and
    the direction of the tail. Alternative to the sequential circular arches.

    :param im: image to process
    :param start_x: starting point x
    :param start_y: starting point y
    :param tail_len_x: tail length on x
    :param tail_len_y: tail length on y
    :param n_segments: number of desired segments
    :param window_size: size in pixel of the window for center-of-mass calculation
    :return:
    """
    if inverted:
        im = (255-im).astype(np.uint8)  # invert image
    length_tail = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)  # calculate tail length
    seg_length = int(length_tail / n_segments)  # segment length from tail length and n of segments

    # Initial displacements in x and y:
    disp_x = int(tail_len_x / n_segments)
    disp_y = int(tail_len_y / n_segments)

    cum_sum = 0  # cumulative tail sum
    points = [(start_x, start_y, 0, cum_sum)]  # output with points
    for i in range(1, n_segments):
        pre_disp_x = disp_x  # save previous displacements for angle calculation
        pre_disp_y = disp_y
        # Use next segment function for find next point with center-of-mass displacement:
        start_x, start_y, disp_x, disp_y, acc = \
            _next_segment(im, start_x, start_y, disp_x, disp_y, window_size, seg_length)

        if i > 1:  # update cumulative angle sum
            new_angle = angle(pre_disp_x, pre_disp_y, disp_x, disp_y)
            cum_sum = cum_sum + new_angle
        points.append((start_x, start_y, acc, cum_sum))

    return points




@jit(nopython=True, cache=True)
def find_fish_midline(im, xm, ym, angle, r=9, m=3, n_points_max=20, n_points_begin=2):
    """ Finds a midline for a fish image, with the starting point and direction
    found by the fish start function
    it goes first a bit in the direction of the tail, and then back,
     so the starting point is refined

    :param im: image to find tail
    :param xm:
    :param ym:
    :param angle:
    :param r:
    :param m:
    :param n_points_max:
    :param n_points_begin:
    :return:
    """
    dx = np.cos(angle) * m
    dy = np.sin(angle) * m

    # go towards the midline
    for i in range(n_points_begin):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)

    # turn back
    dx = -dx
    dy = -dy
    # and follow the midline to the new beginning
    for i in range(n_points_begin):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)

    # turn again and find the whole tail
    dx = -dx
    dy = -dy
    points = [(xm, ym, 0)]
    for i in range(1, n_points_max):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)
        if xm > 0:
            points.append((xm, ym, acc))
    return points