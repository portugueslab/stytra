import cv2
import numpy as np
from numba import jit, jitclass, int64, float64

from stytra.tracking.tail import find_fish_midline
from stytra.tracking.preprocessing import BackgroundSubtractor

from itertools import chain

from lightparam import Param
from stytra.tracking.simple_kalman import predict_inplace, update_inplace
from stytra.tracking.pipelines import ImageToDataNode, NodeOutput
from collections import namedtuple


def _fish_column_names(i_fish, n_segments):
    return [
        "f{:d}_x".format(i_fish),
        "f{:d}_vx".format(i_fish),
        "f{:d}_y".format(i_fish),
        "f{:d}_vy".format(i_fish),
        "f{:d}_theta".format(i_fish),
        "f{:d}_vtheta".format(i_fish),
    ] + ["f{:d}_theta_{:02d}".format(i_fish, i) for i in range(n_segments)]


class FishTrackingMethod(ImageToDataNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, name="fish_tracking", **kwargs)
        self.monitored_headers = ["biggest_area", "f0_theta"]
        self.diagnostic_image_options = [
            "background difference",
            "thresholded background difference",
            "fish detection",
            "thresholded for eye and swim bladder",
        ]

        self.bg_subtractor = BackgroundSubtractor()
        self.dilation_kernel = np.ones((3, 3), dtype=np.uint8)
        self.fishes = None

    def changed(self, vals):
        if any(p in vals.keys() for p in ["n_segments", "n_fish_max", "bg_downsample"]) or \
           vals.get("reset", False):
            self.reset()

    def reset(self):
        self._output_type = namedtuple("t",  list(
            chain.from_iterable(
                [
                    _fish_column_names(i_fish, self._params.n_segments - 1)
                    for i_fish in range(self._params.n_fish_max)
                ]
            )
        ) + ["biggest_area"])
        self._output_type_changed = True

        self.bg_subtractor = BackgroundSubtractor()
        # used for booking a spot for one of the potentially tracked fish
        self.fishes = Fishes(self._params.n_fish_max, n_segments=self._params.n_segments - 1,
                             pos_std=self._params.pos_uncertainty,
                             pred_coef = self._params.prediction_uncertainty,
                             angle_std= np.pi / 10,
                             persist_fish_for = self._params.persist_fish_for)

    def _process(
        self,
        bg,
        n_fish_max: Param(1, (1, 50)),
        n_segments: Param(10, (2, 30)),
        bg_downsample: Param(1, (1, 8)),
        bg_dif_threshold: Param(25, (0, 255)),
        threshold_eyes: Param(35, (0, 255)),
        pos_uncertainty: Param(
            1.0,
            (0, 10.0),
            desc="Uncertainty in pixels about the location of the head center of mass",
        ),
        persist_fish_for: Param(
            2,
            (1, 50),
            desc="How many frames does the fish persist for if it is not detected",
        ),
        prediction_uncertainty: Param(0.1, (0.0, 10.0, 0.0001)),
        fish_area: Param((200, 1200), (1, 4000)),
        border_margin: Param(5, (0, 100)),
        tail_length: Param(60.0, (1.0, 200.0)),
        tail_track_window: Param(3, (3, 70))
    ):

        # update the previously-detected fish using the Kalman filter
        if self.fishes is None:
            self.reset()
        else:
            self.fishes.predict()

        area_scale = bg_downsample * bg_downsample
        border_margin = border_margin // bg_downsample

        # downsample background
        if bg_downsample > 1:
            bg_small = cv2.resize(bg, None, fx=1 / bg_downsample, fy=1 / bg_downsample)
        else:
            bg_small = bg

        bg_thresh = cv2.dilate(
            (bg_small > bg_dif_threshold).view(dtype=np.uint8), self.dilation_kernel
        )

        # find regions where there is a difference with the background
        n_comps, labels, stats, centroids = cv2.connectedComponentsWithStats(bg_thresh)

        try:
            max_area = np.max(stats[1:, cv2.CC_STAT_AREA]) * area_scale
        except ValueError:
            max_area = 0

        # iterate through all the regions different from the background and try
        # to find fish

        messages = []

        nofish = True
        for row, centroid in zip(stats, centroids):
            # check if the contour is fish-sized and central enough
            if not fish_area[0] < row[cv2.CC_STAT_AREA] * area_scale < fish_area[1]:
                continue

            # find the bounding box of the fish in the original image coordinates
            ftop, fleft, fheight, fwidth = (
                int(round(row[x] * bg_downsample))
                for x in [
                    cv2.CC_STAT_TOP,
                    cv2.CC_STAT_LEFT,
                    cv2.CC_STAT_HEIGHT,
                    cv2.CC_STAT_WIDTH,
                ]
            )

            if not (
                (fleft - border_margin >= 0)
                and (fleft + fwidth + border_margin < bg.shape[1])
                and (ftop - border_margin >= 0)
                and (ftop + fheight + border_margin < bg.shape[0])
            ):
                messages.append("W:An object of right area found outside margins")
                continue

            # how much is this region shifted from the upper left corner of the image
            cent_shift = np.array([fleft - border_margin, ftop - border_margin])

            slices = (
                slice(ftop - border_margin, ftop + fheight + border_margin),
                slice(fleft - border_margin, fleft + fwidth + border_margin),
            )

            # take the region and mask the background away to aid detection
            fishdet = bg[slices].copy()

            # estimate the position of the head
            fish_coords = fish_start(fishdet, threshold_eyes)

            # if no actual fish was found here, continue on to the next connected component
            if fish_coords[0] == -1:
                messages.append("W:No appropriate tail start position found")
                continue

            head_coords_up = fish_coords + cent_shift

            theta = _fish_direction_n(bg, head_coords_up, int(round(tail_length / 2)))

            # find the points of the tail
            points = find_fish_midline(
                bg,
                *head_coords_up,
                theta,
                tail_track_window,
                tail_length / n_segments,
                n_segments + 1,
            )

            # convert to angles
            angles = np.mod(points_to_angles(points) + np.pi, np.pi * 2) - np.pi
            if len(angles) == 0:
                messages.append("W:Tail not completely detectable")
                continue

            # also, make the angles continuous
            angles[1:] = np.unwrap(angles[1:] - angles[0])

            # put the data together for one fish
            fish_coords = np.concatenate([np.array(points[0][:2]), angles])

            nofish = False
            # check if this is a new fish, or it is an update of
            # a fish detected previously
            if self.fishes.update(fish_coords):
                messages.append(
                    "I:Updated previous fish")
            elif self.fishes.add_fish(fish_coords):
                messages.append("I:Added new fish")
            else:
                messages.append("E:More fish than n_fish max")

        if nofish:
            messages.append("W:No object of right area, between {:.0f} and {:.0f}".format(
                *fish_area))

        # if a debugging image is to be shown, set it
        if self.set_diagnostic == "background difference":
            self.diagnostic_image = bg
        elif self.set_diagnostic == "thresholded background difference":
            self.diagnostic_image = bg_thresh
        elif self.set_diagnostic == "fish detection":
            fishdet = bg_small.copy()
            fishdet[bg_thresh == 0] = 0
            self.diagnostic_image = fishdet
        elif self.set_diagnostic == "thresholded for eye and swim bladder":
            self.diagnostic_image = np.maximum(bg, threshold_eyes) - threshold_eyes

        if self._output_type is None:
            self.reset_state()

        return NodeOutput(messages,
                          self._output_type(*self.fishes.coords.flatten(),
                                            max_area * 1.0))


spec = [
    ("n_fish", int64),
    ("coords", float64[:, :]),
    ("i_not_updated", int64[:]),
    ("F", float64[:, :]),
    ("uncertainties", float64[:]),
    ("Q", float64[:, :]),
    ("Ps", float64[:, :, :, :]),
    ("def_P", float64[:, :, :]),
    ("persist_fish_for", int64)
]

@jitclass(spec)
class Fishes(object):
    def __init__(self, n_fish_max, pos_std, angle_std, n_segments,
                 pred_coef, persist_fish_for):
        self.n_fish = n_fish_max
        self.coords = np.full((n_fish_max, 6+n_segments), np.nan)
        self.uncertainties = np.array((pos_std, angle_std, angle_std))
        self.def_P = np.zeros((3, 2, 2))
        for i, uc in enumerate(self.uncertainties):
            self.def_P[i, 0, 0] = uc
            self.def_P[i, 1, 1] = uc
        self.i_not_updated = np.zeros(n_fish_max, dtype=np.int64)
        self.Ps = np.zeros((n_fish_max, 3, 2, 2))
        self.F = np.array([[1.0, 1.0], [0.0, 1.0]])
        dt = 0.02
        self.Q = np.array([[0.25 * dt ** 4, 0.5 * dt ** 3],
                           [0.5 * dt ** 3, dt ** 2]]) * pred_coef
        self.persist_fish_for = persist_fish_for

    def predict(self):
        for i_fish in range(self.n_fish):
            if not np.isnan(self.coords[i_fish, 0]):
                for i_coord in range(0, 6, 2):
                    predict_inplace(self.coords[i_fish, i_coord:i_coord+2],
                                    self.Ps[i_fish, i_coord//2], self.F, self.Q)
                self.i_not_updated[i_fish] += 1
                if self.i_not_updated[i_fish] > self.persist_fish_for:
                    self.coords[i_fish, :] = np.nan

    def update(self, new_fish):
        for i_fish in range(self.n_fish):
            if not np.isnan(self.coords[i_fish, 0]):
                if self.is_close(new_fish, i_fish) and self.i_not_updated[i_fish] != 0:
                    # update position with Kalman filtering
                    for i_coord in range(0, 3):
                        # if it is the angle find the modulo 2pi closest
                        nc = new_fish[i_coord]
                        if i_coord == 2:
                            nc = _minimal_angle_dif(self.coords[i_fish, 4], nc)
                        update_inplace(nc,
                                       self.coords[i_fish, i_coord*2:i_coord*2+2],
                                       self.Ps[i_fish, i_coord],
                                       self.uncertainties[i_coord])
                    # update tail angles
                    self.coords[i_fish, 6:] = new_fish[3:]
                    self.i_not_updated[i_fish] = 0
                    return True

    def add_fish(self, new_fish):
        for i_fish in range(self.n_fish):
            if np.isnan(self.coords[i_fish, 0]):
                self.coords[i_fish, 0:6:2] = new_fish[:3]
                self.coords[i_fish, 1:6:2] = 0.0
                self.coords[i_fish, 6:] = new_fish[3:]
                self.Ps[i_fish] = self.def_P
                self.i_not_updated[i_fish] = 0
                return True
        return False

    def is_close(self, new_fish, i_fish):
        """ Check whether the new coordinates are
        within a certain number of pixels of the old estimate
        and within a certain angle
        """
        n_px = 15
        d_theta = np.pi / 2
        dists = new_fish[:2] - self.coords[i_fish, 0:4:2]
        dtheta = np.abs(
            np.mod(new_fish[2] - self.coords[i_fish, 4] + np.pi, np.pi * 2) - np.pi
        )

        return np.sum(dists ** 2) < n_px ** 2 and dtheta < d_theta


@jit(nopython=True)
def points_to_angles(points):
    angles = np.empty(len(points) - 1, dtype=np.float64)
    for i, (p1, p2) in enumerate(zip(points[0:-1], points[1:])):
        angles[i] = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    return angles


@jit(nopython=True)
def fish_start(mask, take_min):
    su = 0.
    ret = np.full((2,), 0.0)
    for i in range(mask.shape[0]):
        for j in range(mask.shape[1]):
            if mask[i, j] > take_min:
                dm = mask[i, j] - take_min
                ret[1] += dm * i
                ret[0] += dm * j
                su += dm

    if su > 0.0:
        return ret / su
    else:
        ret[:] = -1
        return ret


# Utilities for drawing circles.


@jit(nopython=True)
def _symmetry_points(x0, y0, x, y):
    return [
        (x0 + x, y0 + y),
        (x0 - x, y0 + y),
        (x0 + x, y0 - y),
        (x0 - x, y0 - y),
        (x0 + y, y0 + x),
        (x0 - y, y0 + x),
        (x0 + y, y0 - x),
        (x0 - y, y0 - x),
    ]


@jit(nopython=True)
def _circle_points(x0, y0, radius):
    """ Bresenham's circle algorithm

    Parameters
    ----------
    xc : center x
    yc : center y
    r : radius

    Returns
    -------
    a list of points

    """
    f = 1 - radius
    ddf_x = 1
    ddf_y = -2 * radius
    x = 0
    y = radius
    points = [
        (x0, y0 + radius),
        (x0, y0 - radius),
        (x0 + radius, y0),
        (x0 - radius, y0),
    ]
    while x < y:
        if f >= 0:
            y -= 1
            ddf_y += 2
            f += ddf_y
        x += 1
        ddf_x += 2
        f += ddf_x
        points.extend(_symmetry_points(x0, y0, x, y))
    return points


@jit(nopython=True)
def _fish_direction_n(image, start_loc, radius):
    centre_int = start_loc.astype(np.int16)
    pixels_rad = _circle_points(centre_int[0], centre_int[1], radius)
    max_point = pixels_rad[0]
    max_val = 0
    h, w = image.shape
    for x, y in pixels_rad:
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        if image[y, x] > max_val:
            max_val = image[y, x]
            max_point = (x, y)
    return np.arctan2(max_point[1] - centre_int[1], max_point[0] - centre_int[0])


@jit(nopython=True)
def _minimal_angle_dif(th_old, th_new):
    return th_old + np.mod(th_new - th_old + np.pi, np.pi * 2) - np.pi
