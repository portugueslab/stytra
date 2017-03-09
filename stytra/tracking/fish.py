import numpy as np
import cv2
from stytra.tracking.tail import detect_tail_unknown_dir
from numba import vectorize, uint8
from stytra.tracking.tail import find_fish_midline
from stytra.tracking.diagnostics import draw_fish_old

from numba import jit

import param as pa
from stytra.metadata import Metadata


class ContourScorer:
    def __init__(self, target_area, target_ratio, ratio_weight=1):
        self.target_area = target_area
        self.target_ratio = target_ratio
        self.ratio_weight = ratio_weight

    def score(self, cont):
        area = cv2.contourArea(cont)
        if area < 2:
            return 10000
        err_area = ((area-self.target_area)/self.target_area)**2
        _, el_axes, _ = cv2.minAreaRect(cont)
        if el_axes[0] == 0.0:
            ratio = 0.0
        else:
            ratio = el_axes[1]/el_axes[0]
            if ratio > 1:
                ratio = 1/ratio
        err_ratio = (ratio-self.target_ratio)**2

        return self.ratio_weight * err_ratio + err_area

    def best_n(self, contours, n=1):
        idxs = np.argsort([self.score(cont) for cont in contours])
        if n == 1:
            return contours[idxs[0]]
        else:
            return [contours[idxs[i]] for i in range(n)]

    def above_threshold(self, contours, threshold):
        print([self.score(cont) for cont in contours])
        good_conts = [cont for cont in contours if self.score(cont) < threshold]
        return good_conts


class EyeMeasurement:
    def __init__(self):
        self.eyes = np.array([[0, 0], [0, 0]])

    def update(self, eyes):
        self.eyes = eyes

    def dx(self):
        return self.eyes[1][0]-self.eyes[0][0]

    def dy(self):
        return self.eyes[1][1]-self.eyes[0][1]

    def perpendicular(self):
        return np.arctan2(-self.dx(), self.dy())

    def centre(self):
        return np.mean(self.eyes, 0)


def detect_eyes_tail(frame, frame_tail, start_x, start_y, params, diag_image=None):
    # find the eyes
    ret, thresh_eyes = cv2.threshold(frame, params['eye_threshold'], 255,
                                     cv2.THRESH_BINARY)
    diag_image[start_y:start_y+frame.shape[0],
               start_x:start_x + frame.shape[1]] = thresh_eyes
    _, eye_conts, _ = cv2.findContours(255 - thresh_eyes.copy(),
                                       cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
    # if no eye contours are present return error state
    if len(eye_conts) < 3:
        # erode to escape that sometimes eyes connect
        thresh_eyes = cv2.dilate(thresh_eyes, np.ones((3, 3), dtype=np.uint8))
        _, eye_conts, _ = cv2.findContours(255 - thresh_eyes.copy(),
                                           cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_NONE)

        if len(eye_conts) < 2:
            return -1, 0, 0, 0

    # find the darkest two contours which will presumably be eyes
    brightnesses = np.empty(len(eye_conts))
    for idx, eye_cont in enumerate(eye_conts):
        x, y, w, h = cv2.boundingRect(eye_cont)
        if cv2.contourArea(eye_cont) < 3:
            brightnesses[idx] = 255
        else:
            brightnesses[idx] =  \
            (np.mean(frame_tail[start_y + y:start_y + y + h,
                                start_x + x:start_x + x + w].flatten()))
            if diag_image is not None:
                cv2.putText(diag_image, str(brightnesses[idx]),
                            (start_x+x, start_y+y), cv2.FONT_HERSHEY_PLAIN, 0.5, 0)

    order = np.argsort(brightnesses)
    eye_locs = np.empty((2, 2))
    for i in range(2):
        eye_locs[i] = np.mean(eye_conts[order[i]], 0)

    centre_eyes = np.array([start_x, start_y]) + np.mean(eye_locs, 0)

    fish_length = params['fish_length']
    tail_len = fish_length * params['tail_to_body_ratio']
    eyes_to_tail = fish_length * params['tail_start_from_eye_centre']

    dir_tail, tail_angles = detect_tail_unknown_dir(image=(255 - frame_tail),
                                                    start_point=centre_eyes.copy(),
                                                    tail_length=tail_len,
                                                    eyes_to_tail=eyes_to_tail,
                                                    segments=params['n_tail_segments'])

    theta = dir_tail - tail_angles[0]

    tail_segment = (eyes_to_tail) * np.array([np.cos(dir_tail), np.sin(dir_tail)]) + \
                   (tail_len /params['n_tail_segments']) * np.array([np.cos(theta), np.sin(theta)])
    dir_fish = np.arctan2(tail_segment[1], tail_segment[0]) + np.pi

    return centre_eyes[0], centre_eyes[1], dir_fish, -tail_angles


@vectorize([uint8(uint8, uint8)])
def bgdif(x, y):
    if x > y:
        return x-y
    else:
        return y-x


def detect_fishes(frame, mask, params, diagnostics=False):
    kernel = np.ones((7, 7), np.uint8)
    mask2 = cv2.dilate(mask.copy(), kernel)
    ms, contours, orn = cv2.findContours(mask2, cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_NONE)

    # if there are no contours, report no fish in this frame
    if len(contours) == 0:
        if diagnostics:
            return [], frame.copy()
        else:
            return []

    # find the contours corresponding to a fish
    measurements = []
    if diagnostics:
        display = frame.copy()
        diag_image = frame.copy()
    else:
        diag_image = None

    for fish_contour in contours:
        if np.abs(cv2.contourArea(fish_contour) - params['target_area']) < \
                params['area_tolerance']:
            # work only on the part of the image containing the fish
            fx, fy, fw, fh = cv2.boundingRect(fish_contour)
            if diagnostics:
                cv2.rectangle(display, (fx, fy), (fx+fw, fy+fh), 200)
                cv2.putText(display, str(cv2.contourArea(fish_contour)),
                            (fx + fw, fy + fh), cv2.FONT_HERSHEY_PLAIN, 1, 0)
            eye_frame = frame[fy:fy + fh, fx:fx + fw]#np.maximum(frame[fy:fy + fh, fx:fx + fw],
                                    #255 - mask[fy:fy + fh, fx:fx + fw])
            x, y, theta, tail_angles = detect_eyes_tail(eye_frame, frame, fx, fy, params, diag_image)
            if x < 0:
                continue
            res = dict(x=x, y=y, theta=theta, tail_angles=-tail_angles)
            res2 = dict(x=x, y=y, theta=theta)
            for i, ta in enumerate(tail_angles):
                res2['tail_{:02d}'.format(i)] = ta
            if diagnostics:
                draw_fish(display, res, params)
            measurements.append(res2)
    if diagnostics:
        return measurements, np.vstack([display, diag_image])
    return measurements


class MidlineDetectionParams(Metadata):
    target_area = pa.Integer(450, (0, 700))
    area_tolerance = pa.Integer(320, (0, 700))
    n_tail_segments = pa.Integer(18, (1, 20))
    tail_segment_length = pa.Number(4., (0.5, 10))
    tail_detection_radius = pa.Integer(9, (1, 15))
    n_tail_points_return = pa.Integer(2, (0, 10))
    n_points_skip = pa.Integer(2, (0, 10))
    background_noise_sigma = pa.Number(5, (0.1, 20))
    background_ratio = pa.Number(0.5, (0.0, 1.0))


def detect_fish_midline(frame, mask, params):
    """

    :param frame:
    :param mask:
    :param params:
    :return: list containing the starting point and all the angles
    """
    _, contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_NONE)

    # if there are no contours, report no fish in this frame
    if len(contours) == 0:
            return []

    # find the contours corresponding to a fish
    measurements = []
    skip_points=params['n_points_skip']

    for fish_contour in contours:
        if np.abs(cv2.contourArea(fish_contour) - params['target_area']) < \
                params['area_tolerance']:
            fx, fy, fw, fh = cv2.boundingRect(fish_contour)

            # crop the frame around the contour
            mc = mask[fy:fy + fh, fx:fx + fw]
            fc = (255 - frame[fy:fy + fh, fx:fx + fw]) * (mc // 255)

            # find the beginning
            y0, x0, angle = fish_start(mc)
            if y0 < 0:
                continue

            # find the midline (while also refining the beginning)
            points = find_fish_midline(fc, x0, y0, angle,
                                       m=params['tail_segment_length'],
                                       r=params['tail_detection_radius'],
                                       n_points_max=params['n_tail_segments'],
                                       n_points_begin=params['n_tail_points_return'])
            angles = []
            for p1, p2 in zip(points[skip_points:-1], points[skip_points+1:]):
                angles.append(np.arctan2(p2[1]-p1[1],
                                         p2[0] - p1[0]))
            if len(angles) == 0:
                continue
            while len(angles) < params['n_tail_segments']:
                angles.append(angles[-1])

            measurements.append([points[skip_points][0]+fx, points[skip_points][1]+fy] + angles)

    return measurements


def fish_start(mask):
    mom = cv2.moments(cv2.erode(mask,np.ones((7,7), dtype=np.uint8)))
    if mom['m00'] == 0:
        return -1, -1, 0
    y0 = mom['m01']/mom['m00']
    x0 = mom['m10']/mom['m00']
    angle = np.arctan2(mask.shape[0]/2 - y0, mask.shape[1]/2 - x0)
    return y0, x0, angle



if __name__ == '__main__':
    test = np.zeros((100, 100), dtype=np.uint8)
    test[10:20, 10:20] = 255
    ms, contours, orn = cv2.findContours(test.copy(),
                                         cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_NONE)
    print(len(contours))