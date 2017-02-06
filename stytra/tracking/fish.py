import numpy as np
import cv2
from stytra.tracking.tail import detect_tail
from numba import vectorize, uint8


class ContourScorer:
    def __init__(self, target_area, target_ratio, ratio_weight=1):
        self.target_area = target_area
        self.target_ratio = target_ratio
        self.ratio_weight = ratio_weight

    def score(self, cont):
        area = cv2.contourArea(cont)
        if area<2:
            return 10000
        err_area = ((area-self.target_area)/self.target_area)**2
        _, el_axes, _ = cv2.minAreaRect(cont)
        if el_axes[0]==0.0:
            ratio = 0.0
        else:
            ratio = el_axes[1]/el_axes[0]
            if ratio > 1:
                ratio = 1/ratio
        err_ratio = (ratio-self.target_ratio)**2

        return self.ratio_weight*err_ratio+err_area

    def best_n(self, contours, n=1):
        idxs = np.argsort([self.score(cont) for cont in contours])
        if n==1:
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


def detect_eyes_tail(frame, params):
    eye_scorer = ContourScorer(params['eye_area_ratio']*params['target_area'],
                               params['eye_aspect'])
    ret, thresh_eyes = cv2.threshold(frame, params['eye_threshold'], 255,
                                     cv2.THRESH_BINARY)
    _, eye_conts, _ = cv2.findContours(255 - thresh_eyes.copy(),
                                       cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
    # if no eye contours are present return error state
    if len(eye_conts) < 2:
        return -1, 0, 0, 0

    eye_locs = np.empty((2, 2))
    for idx, eye_cont in enumerate(eye_scorer.best_n(eye_conts, 2)):
        eye_locs[idx] = np.mean(eye_cont, 0)

    fish_length = np.sqrt(params['target_area']) * params['length_scaling']

    eyes = EyeMeasurement()
    eyes.update(eye_locs)

    # find the direction in which to start fitting the tail
    dir_tail = eyes.perpendicular()
    centre_eyes = eyes.centre()

    # get which quadrant of the image of the fish we are
    #  looking at (to determine the right angle)
    fw = frame.shape[1]
    eyedir = np.arctan2(eye_locs[1][1] - fw / 2.0,
                        eye_locs[1][0] - fw / 2.0) + np.pi
    if eyedir > 2 * np.pi:
        eyedir -= 2 * np.pi

    if 3 * np.pi / 2 > abs(eyedir - dir_tail) > np.pi / 2:
        dir_tail += np.pi

    tail_start = centre_eyes + fish_length * params[
        'tail_start_from_eye_centre'] * np.array(
        [np.cos(dir_tail), np.sin(dir_tail)])

    tail_len = fish_length * params['tail_to_body_ratio']
    tail_angles = detect_tail(255 - frame, tail_start,
                        dir_tail, tail_len,
                        segments=params['n_tail_segments'])

    theta = dir_tail + tail_angles[0]
    tail_begin = tail_start + (tail_start/params['n_tail_segments'])* np.array([np.cos(theta),
                                               np.sin(theta)])
    dir_fish = np.arctan2(centre_eyes[1]-tail_begin[1], centre_eyes[0]-tail_begin[0])
    tail_angles[0] -= dir_fish-(dir_tail+np.pi)
    return centre_eyes[0], centre_eyes[1], dir_fish, tail_angles


@vectorize([uint8(uint8, uint8)])
def bgdif(x, y):
    if x>y:
        return x-y
    else:
        return y-x


def detect_fishes(frame, mask, params):
    print(np.max(mask))
    ms, contours, orn = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_NONE)

    # if there are no contours, report no fish in this frame
    if len(contours) == 0:
        return []

    # find the contours corresponding to a fish
    measurements = []
    for fish_contour in contours:
        if np.abs(cv2.contourArea(fish_contour) - params['target_area']) < \
                params['area_tolerance']:
            # work only on the part of the image containing the fish
            fx, fy, fw, fh = cv2.boundingRect(fish_contour)
            fish_frame = np.maximum(frame[fy:fy + fh, fx:fx + fw],
                                    255 - mask[fy:fy + fh, fx:fx + fw])
            x, y, theta, tail_angles = detect_eyes_tail(fish_frame, params)
            if x < 0:
                continue
            measurements.append(
                dict(x=x + fx, y=y + fy, theta=theta, tail_angles=tail_angles))
            # display_img_array(fish_frame, inverted=False)

    return measurements

if __name__ == '__main__':
    test = np.zeros((100,100), dtype=np.uint8)
    test[10:20,10:20] = 255
    ms, contours, orn = cv2.findContours(test.copy(),
                                         cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_NONE)
    print(len(contours))
