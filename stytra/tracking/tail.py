import numpy as np
from numba import jit
import cv2


def reduce_to_pi(angle):
    return np.mod(angle, 2*np.pi)-np.pi


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


@jit(nopython=True, cache=True)
def angle(dx1, dy1, dx2, dy2):
    """Calculate angle between two segments d1 and d2
    :param dx1: x length for first segment
    :param dy1: y length for first segment
    :param dx2: -
    :param dy2: -
    :return: angle between -pi and +pi
    """
    alph1 = np.arctan2(dy1, dx1)
    alph2 = np.arctan2(dy2, dx2)
    diff = alph2 - alph1
    if diff >= np.pi:
        diff -= 2*np.pi
    if diff <= -np.pi:
        diff += 2*np.pi
    return diff


def bp_filter_img(img, small_square=3, large_square=50):
    """ Bandpass filter for images.
    :param img: input image
    :param small_square: small square for low-pass smoothing
    :param large_square: big square for high pass smoothing (subtraction of background shades)
    :return: filtered image
    """
    img_filt_lower = cv2.boxFilter(img, -1, (large_square, large_square))
    img_filt_low = cv2.boxFilter(img, -1, (small_square, small_square))
    return cv2.absdiff(img_filt_low, img_filt_lower)


@jit(nopython=True)
def _next_segment(fc, xm, ym, dx, dy, halfwin, next_point_dist):
    """ Find the endpoint of the next tail segment
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
    halfwin2 = halfwin**2
    y_max, x_max = fc.shape
    xs = min(max(int(round(xm + dx - halfwin)), 0), x_max)
    xe = min(max(int(round(xm + dx + halfwin)), 0), x_max)
    ys = min(max(int(round(ym + dy - halfwin)), 0), y_max)
    ye = min(max(int(round(ym + dy + halfwin)), 0), y_max)

    # at the edge returns invalid data
    if xs == xe and ys == ye:
        return -1, -1, 0, 0, 0

    # accumulators
    acc = 0.0
    acc_x = 0.0
    acc_y = 0.0
    for x in range(xs, xe):
        for y in range(ys, ye):
            lx = (xs+halfwin-x)**2
            ly = (ys+halfwin-y)**2
            if lx+ly <= halfwin2:
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


def trace_tail_centroid(im, start_x=0, start_y=0, tail_length_x=1,
                        tail_length_y=1, n_segments=12, window_size=7,
                        color_invert=False, filter_size=0, image_scale=0.5):
    """ Finds the tail for an embedded fish, given the starting point and
    the direction of the tail. Alternative to the sequential circular arches.

    :param im: image to process
    :param start_x: starting point x
    :param start_y: starting point y
    :param tail_length_x: tail length on x
    :param tail_length_y: tail length on y
    :param n_segments: number of desired segments
    :param window_size: size in pixel of the window for center-of-mass calculation
    :param color_invert: True for inverting luminosity of the image
    :param filter_size: Size of the box filter to filter the image
    :param image_scale: the amount of downscaling of the image
    :return: list of cumulative sum + list of angles
    """
    n_segments += 1
    if image_scale != 1:  # bandpass filter the image:
        im = cv2.resize(im, None, fx=image_scale, fy=image_scale, interpolation=cv2.INTER_AREA)
    if filter_size > 0:
        im = cv2.boxFilter(im, -1, (filter_size, filter_size))
    if color_invert:
        im = (255 - im)  # invert image
    length_tail = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2) * image_scale  # calculate tail length
    seg_length = length_tail / n_segments  # segment length from tail length and n of segments

    # Initial displacements in x and y:
    disp_x = tail_length_x * image_scale / n_segments
    disp_y = tail_length_y * image_scale / n_segments

    angles = []
    start_x *= image_scale
    start_y *= image_scale

    halfwin = window_size/2

    for i in range(1, n_segments):
        # Use next segment function for find next point with center-of-mass displacement:
        start_x, start_y, disp_x, disp_y, acc = \
            _next_segment(im, start_x, start_y, disp_x, disp_y, halfwin,
                          seg_length)

        abs_angle = np.arctan2(disp_x, disp_y)
        angles.append(abs_angle)

    return [reduce_to_pi(angles[-1]+angles[-2]-angles[0]-angles[1])] + angles[:]



@jit(nopython=True)
def _tail_trace_core_ls(img, start_x, start_y, tail_len_x, tail_len_y,
                        num_points, tail_length, color_invert):
    """
    Tail tracing based on min (or max) detection on arches. Wrapped by tail_trace_ls.
    """
    # Define starting angle based on tail dimensions:
    start_angle = np.arctan2(tail_len_x, tail_len_y)

    # Initialise first angle arch, tail sum and angle list:
    pi2 = np.pi/2
    lin = np.linspace(-pi2 + start_angle, pi2 + start_angle, 25)
    tail_sum = 0.
    angles = np.zeros(num_points+1)

    # Create vector of intensities along the arch:
    intensity_vect = np.zeros(len(lin), dtype=np.int16)
    seglen = tail_length / num_points

    for j in range(num_points):  # Cycle on segments
        # Transform arch angles in x and y coordinates:
        xs = start_x + seglen * np.sin(lin)
        ys = start_y + seglen * np.cos(lin)

        # fill the vector of intensities along the arch
        for i in range(len(xs)):
            yp = int(ys[i])
            xp = int(xs[i])
            if img.shape[1] > xp >= 0 and 0 <= yp < img.shape[0]:  # check image boundaries
                intensity_vect[i] = img[yp, xp]

        # Find minimum or maximum of the arch.
        # This switch is much faster than inverting the entire image.
        if color_invert:
            ident = np.argmin(intensity_vect)
        else:
            ident = np.argmax(intensity_vect)

        if not np.isnan(lin[ident]):
            new_angle = lin[ident]
        else:
            new_angle = angles[j]

        new_angle = reduce_to_pi(new_angle)

        # skip the first angle for the tail sum
        if j > 0:
            tail_sum += reduce_to_pi(new_angle - angles[j])

        angles[j+1] = new_angle

        # The point found will be the starting point of the next arc
        start_x = xs[ident]
        start_y = ys[ident]

        # Create an 120 deg angle depending on the previous one:
        lin = np.linspace(new_angle - pi2, new_angle + pi2, 20)

    angles[0] = tail_sum
    return angles


def trace_tail_angular_sweep(img, start_x=0, start_y=0, tail_length_x=1,
                             tail_length_y=1, n_segments=7, tail_length=None,
                             filter_size=0, color_invert=False):
    """
    Tail tracing based on min (or max) detection on arches. Wraps _tail_trace_core_ls.
    Speed testing: 20 us for a 514x640 image without smoothing, 300 us with smoothing.
    :param img: input image
    :param start_x: tail starting point (x)
    :param start_y: tail starting point (y)
    :param tail_length_x: tail length x (if tail length is fixed, only orientation matters)
    :param tail_length_y: tail length y
    :param n_segments: number of segments
    :param tail_length: total tail length; if unspecified, calculated from tail_len_x and y
    :param filtering: True for smoothing the image
    :param color_invert: True for inverting image colors
    :return:
    """
    # If required smooth the image:
    if filter_size>0:
        img_filt = cv2.boxFilter(img, -1, (filter_size, filter_size))
    else:
        img_filt = img

    # If tail length is not fixed, calculate from tail dimensions:
    if not tail_length:
        tail_length = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2)

    # Use jitted function for the actual calculation:
    angle_list = _tail_trace_core_ls(img_filt, start_x, start_y, tail_length_x, tail_length_y,
                                     n_segments, tail_length, color_invert)


    return angle_list


@jit(nopython=True, cache=True)
def find_fish_midline(im, xm, ym, angle, r=9, m=3, n_points_max=20):
    """ Finds a midline for a fish image, with the starting point and direction

    :param im:
    :param xm:
    :param ym:
    :param angle:
    :param r:
    :param m:
    :param n_points_max:
    :return:
    """

    dx = np.cos(angle) * m
    dy = np.sin(angle) * m

    points = [(xm, ym, 0)]
    for i in range(1, n_points_max):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)
        if xm > 0:
            points.append((xm, ym, acc))
        else:
            return [(-1.0, -1.0, 0.0)]  # if the tail is not completely tracked, return invalid value

    return points

