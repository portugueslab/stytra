import cv2
import numpy as np
from numba import jit

from stytra.tracking.tail import find_fish_midline
from stytra.tracking.preprocessing import BackgorundSubtractor

from itertools import chain

import logging
from lightparam import Param, Parametrized
from stytra.tracking.simple_kalman import NewtonianKalman


def _fish_column_names(i_fish, n_segments):
    return [
        "f{:d}_x".format(i_fish),
        "f{:d}_vx".format(i_fish),
        "f{:d}_y".format(i_fish),
        "f{:d}_vy".format(i_fish),
        "f{:d}_theta".format(i_fish),
        "f{:d}_vtheta".format(i_fish),
    ] + ["f{:d}_theta_{:02d}".format(i_fish, i) for i in range(n_segments)]


class FishTrackingMethod:
    name = "fish"

    def __init__(self):
        super().__init__()
        self.accumulator_headers = None
        self.monitored_headers = None
        self.data_log_name = "fish_track"
        self.bg_subtractor = BackgorundSubtractor()
        self.track_state = None
        self.bg_im = None
        self.previous_fish = []
        self.idx_book = None
        self.dilation_kernel = np.ones((3, 3), dtype=np.uint8)
        self.recorded = None
        self.diagnostic_image = None
        self.logger = logging.getLogger()
        self.params = Parametrized(name="tracking/fish", params=self.detect)
        self.reset_state()

    def reset_state(self):
        self.accumulator_headers = list(
            chain.from_iterable(
                [
                    _fish_column_names(i_fish, self.params.n_segments - 1)
                    for i_fish in range(self.params.n_fish_max)
                ]
            )
        ) + ["biggest_area"]
        self.monitored_headers = (
            ["f{:d}_x".format(i_fish) for i_fish in range(self.params.n_fish_max)]
            + ["f{:d}_theta".format(i_fish) for i_fish in range(self.params.n_fish_max)]
            + ["biggest_area"]
        )
        self.bg_subtractor = BackgorundSubtractor()
        self.previous_fish = []

        # used for booking a spot for one of the potentially tracked fish
        self.idx_book = IndexBooking(self.params.n_fish_max)
        self.recorded = np.full(
            (self.params.n_fish_max, 3 * 2 + self.params.n_segments - 1), np.nan
        )
        self.logger = logging.getLogger()

    def detect(
        self,
        frame,
        reset: Param(False),
        n_fish_max: Param(1, (1, 10)),
        n_segments: Param(10, (2, 30)),
        bg_downsample: Param(1, (1, 8)),
        bg_learning_rate: Param(0.04, (0.0, 1.0)),
        bg_learn_every: Param(400, (1, 10000)),
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
        tail_track_window: Param(3, (3, 70)),
        display_processed: Param(
            "raw",
            [
                "raw",
                "background difference",
                "thresholded background difference",
                "fish detection",
                "thresholded for eye and swim bladder",
            ],
        ),
    ):

        # if the parameters affecting the dimensions of the result changed,
        # reset everything
        if (
            reset
            or n_fish_max != self.params.n_fish_max
            or n_segments != self.params.n_segments
            or bg_downsample != self.params.bg_downsample
        ):
            self.params.params.bg_downsample.value = bg_downsample
            self.params.params.n_segments.value = n_segments
            self.params.params.n_fish_max.value = n_fish_max
            self.reset_state()

        # update the previously-detected fish using the Kalman filter
        for pfish in self.previous_fish:
            pfish.predict()

        area_scale = bg_downsample * bg_downsample
        border_margin = border_margin // bg_downsample

        # subtract background
        bg = self.bg_subtractor.process(frame, bg_learning_rate, bg_learn_every)

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
        new_fish = []

        message = "W:No object of right area, between {:.0f} and {:.0f}".format(*fish_area)

        for row, centroid in zip(stats, centroids):
            # check if the contour is fish-sized and central enough
            if not fish_area[0] < row[cv2.CC_STAT_AREA] * area_scale < fish_area[1]:
                continue

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
                and (fleft + fwidth + border_margin < frame.shape[1])
                and (ftop - border_margin >= 0)
                and (ftop + fheight + border_margin < frame.shape[0])
            ):
                message = "W:An object of right area found outside margins".format(
                    *fish_area
                )
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
                message = "W:No appropriate tail start position found"
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
                message = "W:Tail not completely detectable"
                continue

            # also, make the angles continuous
            angles[1:] = np.unwrap(angles[1:] - angles[0])

            # put the data together for one fish
            fish_coords = np.concatenate([np.array(points[0][:2]), angles])

            # check if this is a new fish, or it is an update of
            # a fish detected previously
            for past_fish in self.previous_fish:
                if past_fish.is_close(fish_coords) and past_fish.i_not_updated < 0:
                    past_fish.update(fish_coords)
                    message = "I:Updated previous fish"
                    break
            # the else executes if no past fish is close, so a new fish
            # has to be instantiated for this measurement
            else:
                if not np.all(self.idx_book.full):
                    new_fish.append(
                        Fish(
                            fish_coords,
                            self.idx_book,
                            pred_coef=prediction_uncertainty,
                            pos_std=pos_uncertainty,
                        )
                    )
                    message = "I:Added new fish"
                else:
                    message = "E:More fish than n_fish max"

        current_fish = []

        # remove fish not detected in two subsequent frames
        for pf in self.previous_fish:
            if pf.i_not_updated < -persist_fish_for:
                self.idx_book.full[pf.i_ar] = False
                self.recorded[pf.i_ar, :] = np.nan
            else:
                current_fish.append(pf)

        # add the new fish to the previously updated fish
        current_fish.extend(new_fish)
        self.previous_fish = current_fish

        # serialize the fish data for queue communication
        for pf in self.previous_fish:
            self.recorded[pf.i_ar, :] = pf.serialize()

        # if a debugging image is to be shown, set it
        if display_processed == "background difference":
            self.diagnostic_image = bg
        elif display_processed == "thresholded background difference":
            self.diagnostic_image = bg_thresh
        elif display_processed == "fish detection":
            fishdet = bg.copy()
            fishdet[bg_thresh == 0] = 0
            self.diagnostic_image = fishdet
        elif display_processed == "thresholded for eye and swim bladder":
            self.diagnostic_image = np.maximum(bg, threshold_eyes) - threshold_eyes

        return message, tuple(self.recorded.flatten()) + (max_area * 1.0,)


class IndexBooking:
    """ Class that keeps track of which array columns
    are free to put in fish data

    """

    def __init__(self, n_max=3):
        self.full = np.zeros(n_max, dtype=np.bool)

    def get_next(self):
        i_next = np.argmin(self.full)
        self.full[i_next] = True
        return i_next


class Fish:
    """ Class for Kalman-filtered tracking of individual fish

    """

    def __init__(
        self, initial_state, idx_book, pos_std=1.0, angle_std=np.pi / 10, pred_coef=1
    ):
        self.i_not_updated = 0
        self.i_ar = idx_book.get_next()

        dt = 0.02
        # the position will be Kalman-filtered
        self.filters = [
            NewtonianKalman(x0, stdev, dt, pred_coef)
            for x0, stdev in zip(initial_state[:3], [pos_std, pos_std, angle_std])
        ]

        self.unfiltered = initial_state[3:]

    def predict(self):
        for f in self.filters:
            f.predict()
        self.i_not_updated -= 1

    def update(self, new_fish_state):
        for i, (f, s) in enumerate(zip(self.filters, new_fish_state[:3])):
            # Angle needs to be updated specially:
            if i == 2:
                s = _minimal_angle_dif(f.x[0], s)
            f.update(s)
        self.unfiltered[:] = new_fish_state[3:]
        self.i_not_updated = 0

    def serialize(self):
        return np.concatenate([f.x.flatten() for f in self.filters] + [self.unfiltered])

    def is_close(self, new_fish, n_px=15, d_theta=np.pi / 2):
        """ Check whether the new coordinates are
        within a certain number of pixels of the old estimate
        and within a certain angle
        """
        dists = np.array(
            [(new_fish[i] - f.x[0]) for i, f in enumerate(self.filters[:2])]
        )
        dtheta = np.abs(
            np.mod(new_fish[2] - self.filters[2].x[0] + np.pi, np.pi * 2) - np.pi
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
