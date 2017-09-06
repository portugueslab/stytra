import numpy as np
from numba import jit
import cv2


@jit(nopython=True)
def detect_segment(detect_angles, seglen, start, direction, image):
    """
    :param detect_angles: a list of angles at which to evaluate the next point
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
def detect_tail(image, start_point, start_dir=0, pixlen=100, segments=5,
                max_segment_angle=np.pi*3/8):
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


def std_bp_filter(img, small_square=3, large_square=50):
    """ Function for returning the standard deviation of an image pixels from the mean after
    band-pass filtering
    """
    filtered = bp_filter_img(img, small_square, large_square)
    return (filtered - int(cv2.mean(filtered)[0])) ** 2


# Can't be jit-ted because of the cv2 library in the filtering
# @jit(nopython=True, cache=True)
def detect_tail_embedded(im, start_x, start_y, tail_len_x, tail_len_y, n_segments=20, window_size=30,
                         color_invert=False, image_filt=False):
    """ Finds the tail for an embedded fish, given the starting point and
    the direction of the tail. Alternative to the sequential circular arches.

    :param im: image to process
    :param start_x: starting point x
    :param start_y: starting point y
    :param tail_len_x: tail length on x
    :param tail_len_y: tail length on y
    :param n_segments: number of desired segments
    :param window_size: size in pixel of the window for center-of-mass calculation
    :param color_invert: True for inverting luminosity of the image
    :param image_filt: True for spatial filtering of the the image
    :return: list of cumulative sum + list of angles
    """
    if image_filt:  # bandpass filter the image:
        im = std_bp_filter(im, small_square=3, large_square=50)
    if color_invert:
        im = (255 - im).astype(np.uint8)  # invert image
    length_tail = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)  # calculate tail length
    seg_length = int(length_tail / n_segments)  # segment length from tail length and n of segments

    # Initial displacements in x and y:
    disp_x = int(tail_len_x / n_segments)
    disp_y = int(tail_len_y / n_segments)

    cum_sum = 0  # cumulative tail sum
    angles = [np.arctan2(tail_len_y, tail_len_x)]
    for i in range(1, n_segments):
        pre_disp_x = disp_x  # save previous displacements for angle calculation
        pre_disp_y = disp_y

        # Use next segment function for find next point with center-of-mass displacement:
        start_x, start_y, disp_x, disp_y, acc = \
            _next_segment(im, start_x, start_y, disp_x, disp_y, window_size, seg_length)

        if i > 1:  # update cumulative angle sum
            new_angle = angle(pre_disp_x, pre_disp_y, disp_x, disp_y)
            abs_angle = np.arctan2(disp_y, disp_x)
            cum_sum = cum_sum + new_angle
            angles.append(abs_angle)

    return [cum_sum, ] + angles[::]


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

@jit(nopython=True)
def reduce_to_pi(angle):
    if angle > np.pi:
        return angle - np.pi*2
    if angle < -np.pi:
        return angle + np.pi * 2
    return angle

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


def tail_trace_ls(img, start_x=0, start_y=0, tail_length_x=1,
                  tail_length_y=1, n_segments=7, tail_length=None,
                  filtering=True, color_invert=False):
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
    if filtering:
        img_filt = cv2.boxFilter(img, -1, (7, 7))
    else:
        img_filt = img

    # If tail length is not fixed, calculate from tail dimensions:
    if not tail_length:
        tail_length = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2)

    # Use jitted function for the actual calculation:
    angle_list = _tail_trace_core_ls(img_filt, start_x, start_y, tail_length_x, tail_length_y,
                                     n_segments, tail_length, color_invert)


    return angle_list
