import numpy as np
import cv2


def a_to_tc(a):
    """ Useful for drawing things with openCV,
    converts arrays to tuples of integers

    :param a:
    :return:
    """
    return tuple(a.astype(np.int))


def draw_fish_old(display, fish_data, params):
    centre_eyes = np.array([fish_data['x'], fish_data['y']])
    fish_length = params['fish_length']
    dir_tail = fish_data['theta'] + np.pi
    tail_start = centre_eyes + fish_length * params[
        'tail_start_from_eye_centre'] * np.array(
        [np.cos(dir_tail), np.sin(dir_tail)]),

    # draw the tail
    seglen = fish_length * params['tail_to_body_ratio'] / params[
        'n_tail_segments']
    abs_angles = dir_tail + np.cumsum(fish_data['tail_angles'])
    points = tail_start + np.cumsum(
        seglen * np.vstack([np.cos(abs_angles), np.sin(abs_angles)]).T, 0)

    display = cv2.circle(display, a_to_tc(centre_eyes), 3, (100, 250, 200))

    for j in range(len(points) - 1):
        display = cv2.line(display, a_to_tc(points[j]),
                                    a_to_tc(points[j + 1]),
                                    (250, 100, 100))

    # draw heading direction
    display = cv2.line(display, a_to_tc(centre_eyes), a_to_tc(
        centre_eyes + np.array([np.cos(fish_data['theta']),
                                np.sin(fish_data['theta'])])*40), (120,100,30))

    return display


def draw_fish_new(display, mes, params):
    if len(display.shape) == 2:
        display = display[:, :, None] * np.ones(3, dtype=np.uint8)[None, None, :]

    points = [np.array([mes['x'], mes['y']])]
    for i, col in enumerate(
            ['th_{:02d}'.format(i) for i in range(params['n_tail_segments'])]):
        points.append(points[-1] + params['tail_segment_length'] * np.array(
            [np.cos(mes[col]), np.sin(mes[col])]))

    points = np.array(points)

    display = cv2.circle(display, a_to_tc(points[0]), 3, (100, 250, 200))

    for j in range(len(points) - 1):
        display = cv2.line(display, a_to_tc(points[j]),
                                    a_to_tc(points[j + 1]),
                                    (250, 100, 100))

    return display


def draw_tail(display, points):
    if len(display.shape) == 2:
        display = display[:, :, None] * np.ones(3, dtype=np.uint8)[None, None, :]

    #points_mtx = np.array(points)[:, -2::-1]
    points_mtx = np.array(points)[:, :2]

    # points = [np.array([mes['x'], mes['y']])]
    # for i, col in enumerate(
    #         ['th_{:02d}'.format(i) for i in range(params['n_tail_segments'])]):
    #     points.append(points[-1] + params['tail_segment_length'] * np.array(
    #         [np.cos(mes[col]), np.sin(mes[col])]))
    #
    # points = np.array(points)
    # print(points)

    for i in range(points_mtx.shape[0]):
        display = cv2.circle(display, a_to_tc(points_mtx[i]), 5, (200, 0, 0))

    for i in range(points_mtx.shape[0] - 1):
        display = cv2.line(display, a_to_tc(points_mtx[i]),
                                    a_to_tc(points_mtx[i+1]),
                                    (250, 100, 100))

    return display
