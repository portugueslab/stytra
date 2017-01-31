import numpy as np
from numba import jit

@jit(nopython=True)
def detect_segment(detect_angles, seglen, start, direction, image, idx=0):
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
