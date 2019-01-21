import numpy as np
from numba import jit
from lightparam import Param, Parametrized
from scipy.ndimage.filters import gaussian_filter1d
from stytra.utilities import reduce_to_pi
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple


class TailTrackingMethod(ImageToDataNode):
    """General tail tracking method."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="tail_tracking", **kwargs)
        self.monitored_headers = ["tail_sum"]
        self.data_log_name = "tail_track"
        self._output_type = None

    def changed(self, vals):
        if "n_output_segments" in vals.keys():
            self.reset()

    def reset(self):
        self._output_type = namedtuple("t", ["tail_sum"] + [
            "theta_{:02}".format(i)
            for i in range(self._params.n_output_segments)
        ])
        #self._output_type_changed = True


class CentroidTrackingMethod(TailTrackingMethod):
    """Center-of-mass method to find consecutive segments."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resting_angles = None
        self.previous_angles = None

    def _process(
        self,
        im,
        tail_start: Param((0.47, 1.7), gui=False),
        tail_length: Param((0.07, -1.36), gui=False),
        n_segments: Param(12, (1, 50)),
        tail_filter_width: Param(0.0, (0.0, 10.0)),
        time_filter_weight: Param(0.0, (0.0, 1.0)),
        n_output_segments: Param(9, (1, 30)),
        reset_zero: Param(False),
        window_size: Param(7, (1, 15)),
        **extraparams
    ):
        """Finds the tail for an embedded fish, given the starting point and
        the direction of the tail. Alternative to the sequential circular arches.

        Parameters
        ----------
        im :
            image to process
        tail_start :
            starting point (x, y) (Default value = 0)
        tail_length :
            tail length (x, y) (Default value = 1)
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
        messages = []
        start_y, start_x = tail_start
        tail_length_y, tail_length_x = tail_length

        scale = im.shape[0]

        # Calculate tail length:
        length_tail = (
            np.sqrt(tail_length_x ** 2 + tail_length_y ** 2)
            * scale
        )

        # Segment length from tail length and n of segments:
        seg_length = length_tail / n_segments

        n_segments += 1

        # Initial displacements in x and y:
        disp_x = tail_length_x * scale / n_segments
        disp_y = tail_length_y * scale / n_segments

        angles = np.full(n_segments - 1, np.nan)
        start_x *= scale
        start_y *= scale

        halfwin = window_size / 2
        for i in range(1, n_segments):
            # Use next segment function for find next point
            # with center-of-mass displacement:
            start_x, start_y, disp_x, disp_y, acc = _next_segment(
                im, start_x, start_y, disp_x, disp_y, halfwin, seg_length
            )
            if start_x < 0:
                messages.append("W:segment {} not detected".format(i))
                break

            abs_angle = np.arctan2(disp_x, disp_y)
            angles[i - 1] = abs_angle

        # we want angles to be continuous, this removes potential 2pi discontinuities
        angles = np.unwrap(angles)

        # we do not need to record a large amount of angles
        if tail_filter_width > 0:
            angles = gaussian_filter1d(angles, tail_filter_width, mode="nearest")

        angles = np.interp(
            np.linspace(0, 1, n_output_segments),
            np.linspace(0, 1, n_segments - 1),
            angles,
        )
        # Interpolate to the desired number of output segments

        if reset_zero:
            if self.resting_angles is None or len(self.resting_angles) != len(angles):
                self.resting_angles = angles
            else:
                self.resting_angles = self.resting_angles * 0.5 + angles * 0.5
        else:
            if self.resting_angles is not None:
                angles = angles - self.resting_angles + self.resting_angles[0]

        if time_filter_weight > 0 and self.previous_angles is not None:
            angles = (
                time_filter_weight * self.previous_angles
                + (1 - time_filter_weight) * angles
            )

        self.previous_angles = angles

        if self._output_type is None:
            self.reset()

        # Total curvature as sum of the last 2 angles - sum of the first 2
        return NodeOutput(
            messages,
            self._output_type(angles[-1] + angles[-2] - angles[0] - angles[1],
                              *angles),
        )


@jit(nopython=True, cache=True)
def find_fish_midline(im, xm, ym, angle, r=9, m=3, n_points=20):
    """Finds a midline for a fish image, with the starting point and direction

    Parameters
    ----------
    im :
        param xm:
    ym :
        param angle:
    r :
        param m: (Default value = 9)
    n_points :
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
    for i in range(1, n_points):
        xm, ym, dx, dy, acc = _next_segment(im, xm, ym, dx, dy, r, m)
        if xm > 0:
            points.append((xm, ym, acc))
        else:
            return [
                (-1.0, -1.0, 0.0)
            ]  # if the tail is not completely tracked, return invalid value

    return points


class AnglesTrackingMethod(TailTrackingMethod):
    """Angular sweep method to find consecutive segments."""

    def __init__(self):
        super().__init__()
        # self.add_params(dark_tail=False)
        self.params = Parametrized(name="tracking/tail_angles", params=self.detect)
        self.accumulator_headers = ["tail_sum"] + [
            "theta_{:02}".format(i) for i in range(self.params.n_segments)
        ]

    def detect(
        self,
        im,
        tail_start: Param((0, 0), gui=False),
        n_segments: Param(7),
        tail_length: Param((1, 1), gui=False),
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

        scale = im.shape[0]

        # Calculate tail length:
        length_tail = (
            np.sqrt(tail_length_x ** 2 + tail_length_y ** 2)
            * scale
        )

        # Initial displacements in x and y:
        disp_x = tail_length_x * scale / n_segments
        disp_y = tail_length_y * scale / n_segments

        start_x *= scale
        start_y *= scale

        # Use jitted function for the actual calculation:
        angle_list = _tail_trace_core_ls(
            im, start_x, start_y, disp_x, disp_y, n_segments, length_tail
        )

        return angle_list


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
def _tail_trace_core_ls(img, start_x, start_y, disp_x, disp_y, num_points, tail_length):
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
