import numpy as np
from numba import jit, guvectorize


def reduce_to_pi(ar):
    """ Reduce angles to the -pi to pi range
    """
    try:
        ar[ar > np.pi] -= np.pi*2
        ar[ar < -np.pi] += np.pi*2
    except TypeError:
        if ar > np.pi:
            ar -= np.pi*2
        elif ar <-np.pi:
            ar += np.pi*2
        else:
            pass
    return ar


def angle_mean(angles, axis=1):
    """ Correct calculation of a mean of an array of angles
    """
    return np.arctan2(np.sum(np.sin(angles), axis),
                      np.sum(np.cos(angles), axis))


def angle_dif(a,b):
    """ Return the difference between to angles/angle arrays respecting circularity
    """
    return np.minimum(np.minimum(np.abs(a-b),
                                 np.abs(a-b+2*np.pi)),
                      np.abs(a-b-2*np.pi))


def cossin(theta):
    """ Return an array of cosine and sine of theta
    """
    return np.array((np.cos(theta), np.sin(theta)))


def transform_affine(points, tm):
    """ Affine transform a point or an array of points with the matrix tm
    """
    padded = np.pad(points,
                    tuple((0,0) for i in range(len(points.shape)-1))+((0,1),),
                    mode='constant', constant_values=1.0)
    return padded @ tm.T


def rot_mat(theta):
    """ The rotation matrix for an angle theta

    :param theta: rotation angle
    :return: rotation matrix
    """
    return np.array([[np.cos(theta), -np.sin(theta)],
                    [np.sin(theta), np.cos(theta)]])


@jit(nopython=True)
def smooth_tail_angles(tail_angles):
    """ Smooths out the tau jumps in tail angles, so that the angle between
    tail segments is smoothly changing

    :param tail_angles:
    :return:
    """

    tau = 2*np.pi

    for i in range(1, tail_angles.shape[0]):
        previous = tail_angles[i - 1]
        dist = np.abs(previous - tail_angles[i])
        if np.abs(previous-(tail_angles[i] + tau)) < dist:
            tail_angles[i] += tau
        elif np.abs(previous-(tail_angles[i] - tau)) < dist:
            tail_angles[i] -= tau

    return tail_angles


@jit(nopython=True)
def smooth_tail_angles_series(tail_angles_series):
    """ Smooths out the tau jumps in tail angles, so that the angle between
    tail segments is smoothly changing, applied on series

    :param tail_angles:
    :return:
    """
    # TODO use guvecotorize to avoid having this function

    for i_t in range(tail_angles_series.shape[0]):
        smooth_tail_angles(tail_angles_series[i_t, :])

    return tail_angles_series
