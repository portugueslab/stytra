import numpy as np
from numba import jit
import cv2
from stytra.tracking import ParametrizedImageproc


class TailTrackingMethod(ParametrizedImageproc):
    """General tail tracking method."""

    def __init__(self, **kwargs):
        super().__init__(name="tracking_tail_params", **kwargs)
        # TODO maybe getting default values here:
        self.add_params(
            n_segments=dict(value=10, type="int", limits=(2, 50)),
            tail_start=dict(value=(440, 225), visible=False),
            tail_length=dict(value=(-250, 30), visible=False),
        )
        self.accumulator_headers = ["tail_sum"] + [
            "theta_{:02}".format(i) for i in range(self.params["n_segments"])
        ]
        self.monitored_headers = ["tail_sum"]
        self.data_log_name = "behaviour_tail_log"


class CentroidTrackingMethod(TailTrackingMethod):
    """Center-of-mass method to find consecutive segments."""

    def __init__(self):
        super().__init__()
        self.add_params(
            window_size=dict(value=30, suffix=" pxs", type="float", limits=(2, 100))
        )

    @classmethod
    def detect(
        cls,
        im,
        tail_start=(0, 0),
        tail_length=(1, 1),
        n_segments=12,
        window_size=7,
        image_scale=1,
        **extraparams
    ):
        """Finds the tail for an embedded fish, given the starting point and
        the direction of the tail. Alternative to the sequential circular arches.

        Parameters
        ----------
        im :
            image to process
        tail_start :
            starting point (x, y) (Default value = (0)
        tail_length :
            tail length (x, y) (Default value = (1)
        n_segments :
            number of desired segments (Default value = 12)
        window_size :
            window size in pixel for center-of-mass calculation (Default value = 7)
        color_invert :
            True for inverting luminosity of the image (Default value = False)
        filter_size :
            Size of the box filter to low-pass filter the image (Default value = 0)
        image_scale :
            the amount of downscaling of the image (Default value = 0.5)
        0) :

        1) :


        Returns
        -------
        type
            list of cumulative sum + list of angles

        """
        start_y, start_x = tail_start
        tail_length_y, tail_length_x = tail_length

        n_segments += 1

        # Calculate tail length:
        length_tail = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2) * image_scale

        # Segment length from tail length and n of segments:
        seg_length = length_tail / n_segments

        # Initial displacements in x and y:
        disp_x = tail_length_x * image_scale / n_segments
        disp_y = tail_length_y * image_scale / n_segments

        angles = []
        start_x *= image_scale
        start_y *= image_scale

        halfwin = window_size / 2
        for i in range(1, n_segments):
            # Use next segment function for find next point
            # with center-of-mass displacement:
            start_x, start_y, disp_x, disp_y, acc = _next_segment(
                im, start_x, start_y, disp_x, disp_y, halfwin, seg_length
            )

            abs_angle = np.arctan2(disp_x, disp_y)
            angles.append(abs_angle)

        return [reduce_to_pi(angles[-1] + angles[-2] - angles[0] - angles[1])] + angles[
            :
        ]


class AnglesTrackingMethod(TailTrackingMethod):
    """Angular sweep method to find consecutive segments."""

    def __init__(self):
        super().__init__()
        self.add_params(dark_tail=False)

    @classmethod
    def detect(
        cls,
        im,
        tail_start=(0, 0),
        n_segments=7,
        tail_length=(1, 1),
        dark_tail=False,
        image_scale=1,
        **extraparams
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
        dark_tail :
            True for inverting image colors (Default value = False)
        im :

        0) :

        1) :

        image_scale :
             (Default value = 1)

        Returns
        -------

        """

        start_y, start_x = tail_start
        tail_length_y, tail_length_x = tail_length

        # Calculate tail length:
        length_tail = np.sqrt(tail_length_x ** 2 + tail_length_y ** 2) * image_scale

        # Initial displacements in x and y:
        disp_x = tail_length_x * image_scale / n_segments
        disp_y = tail_length_y * image_scale / n_segments

        start_x *= image_scale
        start_y *= image_scale

        # Use jitted function for the actual calculation:
        angle_list = _tail_trace_core_ls(
            im, start_x, start_y, disp_x, disp_y, n_segments, length_tail, dark_tail
        )

        return angle_list


@jit(nopython=True)
def reduce_to_pi(angle):
    """

    Parameters
    ----------
    angle :
        

    Returns
    -------

    """
    return np.mod(angle + np.pi, 2 * np.pi) - np.pi


@jit(nopython=True)
def find_direction(start, image, seglen):
    """

    Parameters
    ----------
    start :
        
    image :
        
    seglen :
        

    Returns
    -------

    """
    n_angles = np.ceil(np.pi*2*seglen*2)
    angles = np.arange(n_angles) * np.pi * 2 / n_angles

    detect_angles = angles

    weighted_vector = np.zeros(2)

    for i in range(detect_angles.shape[0]):
        coord = (
            round(start[0] + seglen * np.cos(detect_angles[i])),
            round(start[1] + seglen * np.sin(detect_angles[i])),
        )
        if (
            (coord[0] > 0)
            & (coord[0] < image.shape[1])
            & (coord[1] > 0)
            & (coord[1] < image.shape[0])
        ):
            brg = image[coord[1], coord[0]]

            weighted_vector += brg * np.array(
                [np.cos(detect_angles[i]), np.sin(detect_angles[i])]
            )

    return np.arctan2(weighted_vector[1], weighted_vector[0])


@jit(nopython=True, cache=True)
def angle(dx1, dy1, dx2, dy2):
    """Calculate angle between two segments d1 and d2

    Parameters
    ----------
    dx1 :
        x length for first segment
    dy1 :
        y length for first segment
    dx2 :
        param dy2: -
    dy2 :
        

    Returns
    -------
    type
        angle between -pi and +pi

    """
    alph1 = np.arctan2(dy1, dx1)
    alph2 = np.arctan2(dy2, dx2)
    diff = alph2 - alph1
    if diff >= np.pi:
        diff -= 2 * np.pi
    if diff <= -np.pi:
        diff += 2 * np.pi
    return diff


def bp_filter_img(img, small_square=3, large_square=50):
    """Bandpass filter for images.

    Parameters
    ----------
    img :
        input image
    small_square :
        small square for low-pass smoothing (Default value = 3)
    large_square :
        big square for high pass smoothing (subtraction of background shades) (Default value = 50)

    Returns
    -------
    type
        filtered image

    """
    img_filt_lower = cv2.boxFilter(img, -1, (large_square, large_square))
    img_filt_low = cv2.boxFilter(img, -1, (small_square, small_square))
    return cv2.absdiff(img_filt_low, img_filt_lower)


@jit(nopython=True)
def _next_segment(fc, xm, ym, dx, dy, halfwin, next_point_dist):
    """Find the endpoint of the next tail segment
    by calculating the moments in a look-ahead area

    Parameters
    ----------
    fc :
        image to find tail
    xm :
        starting point x
    ym :
        starting point y
    dx :
        initial displacement x
    dy :
        initial displacement y
    wind_size :
        size of the window to estimate next tail point
    next_point_dist :
        distance to the next tail point
    halfwin :
        

    Returns
    -------

    """

    # Generate square window for center of mass
    halfwin2 = halfwin ** 2
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
            lx = (xs + halfwin - x) ** 2
            ly = (ys + halfwin - y) ** 2
            if lx + ly <= halfwin2:
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


@jit(nopython=True)
def _tail_trace_core_ls(
    img, start_x, start_y, disp_x, disp_y, num_points, tail_length, color_invert
):
    """Tail tracing based on min (or max) detection on arches. Wrapped by
    trace_tail_angular_sweep.

    Parameters
    ----------
    img :
        
    start_x :
        
    start_y :
        
    disp_x :
        
    disp_y :
        
    num_points :
        
    tail_length :
        
    color_invert :
        

    Returns
    -------

    """
    # Define starting angle based on tail dimensions:
    start_angle = np.arctan2(disp_x, disp_y)

    # Initialise first angle arch, tail sum and angle list:
    pi2 = np.pi / 2
    lin = np.linspace(-pi2 + start_angle, pi2 + start_angle, 25)
    tail_sum = 0.
    angles = np.zeros(num_points + 1)

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
            if (
                img.shape[1] > xp >= 0 and 0 <= yp < img.shape[0]
            ):  # check image boundaries
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

        angles[j + 1] = new_angle

        # The point found will be the starting point of the next arc
        start_x = xs[ident]
        start_y = ys[ident]

        # Create an 120 deg angle depending on the previous one:
        lin = np.linspace(new_angle - pi2, new_angle + pi2, 20)

    angles[0] = tail_sum
    return angles


@jit(nopython=True, cache=True)
def find_fish_midline(im, xm, ym, angle, r=9, m=3, n_points_max=20):
    """Finds a midline for a fish image, with the starting point and direction

    Parameters
    ----------
    im :
        param xm:
    ym :
        param angle:
    r :
        param m: (Default value = 9)
    n_points_max :
        return: (Default value = 20)
    xm :
        
    angle :
        
    m :
         (Default value = 3)

    Returns
    -------

    """

    dx = np.cos(angle) * m
    dy = np.sin(angle) * m

    points = [(xm, ym, 0)]
    for i in range(1, n_points_max):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)
        if xm > 0:
            points.append((xm, ym, acc))
        else:
            return [
                (-1.0, -1.0, 0.0)
            ]  # if the tail is not completely tracked, return invalid value

    return points
