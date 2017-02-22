import numpy as np
from numba import jit


@jit(nopython=True)
def detect_segment(detect_angles, seglen, start, direction, image):
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




@jit(nopython=True, cache=True)
def _next_segment(fc, xm, ym, dx, dy, r, m):
    """ Find the enpoint of the next tail segment
    by calculating the moments in a look-ahead area

    :param fc:
    :param xm:
    :param ym:
    :param dx:
    :param dy:
    :param r:
    :param m:
    :return:
    """
    y_max, x_max = fc.shape
    xs = min(max(int(round(xm + dx - r / 2)), 0), x_max)
    xe = min(max(int(round(xm + dx + r / 2)), 0), x_max)
    ys = min(max(int(round(ym + dy - r / 2)), 0), y_max)
    ye = min(max(int(round(ym + dy + r / 2)), 0), y_max)

    if xs == xe and ys == ye:
        return -1, -1, 0, 0, 0

    acc = 0
    acc_x = 0
    acc_y = 0
    for x in range(xs, xe):
        for y in range(ys, ye):
            acc_x += x * fc[y, x]
            acc_y += y * fc[y, x]
            acc += fc[y, x]

    if acc == 0:
        return -1, -1, 0, 0, 0

    mn_y = acc_y / acc - ym
    mn_x = acc_x / acc - xm

    a = np.sqrt(mn_y ** 2 + mn_x ** 2) / m

    if a == 0:
        return -1, -1, 0, 0, 0

    dx = mn_x / a
    dy = mn_y / a

    return xm + dx, ym + dy, dx, dy, acc


@jit(nopython=True, cache=True)
def find_fish_midline(im, xm, ym, angle, r=9, m=3, n_points_max=20, n_points_begin=2):
    """ Finds a midline for a fish image, with the starting point and direction
    found by the fish start function
    it goes first a bit in the direction of the tail, and then back,
     so the starting point is refined

    :param im:
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

    # go towards the midling
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