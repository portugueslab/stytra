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
    max_dir = 0
    max_val = 0
    for i in range(detect_angles.shape[0]):
        coord = (int(start[0] + seglen * np.cos(detect_angles[i])),
                 int(start[1] + seglen * np.sin(detect_angles[i])))
        if ((coord[0] > 0) & (coord[0] < image.shape[1]) &
                (coord[1] > 0) & (coord[1] < image.shape[0])):
            brg = image[coord[1], coord[0]]
            # if brg > max_val:
            #     max_val = brg
            #     max_dir = detect_angles[i]

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
