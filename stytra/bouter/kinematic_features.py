import numpy as np
import pandas as pd
from stytra.bouter.angles import angle_mean, cossin, reduce_to_pi, smooth_tail_angles_series, rot_mat
from scipy.ndimage import gaussian_filter1d
from scipy.signal import medfilt


def normalise_bout(bout, median_len):
    dir_init = angle_mean(bout.theta_00.iloc[0:10])
    coord = np.column_stack(
        [gaussian_filter1d(medfilt(bout[par], median_len), 1) for par in
         ['x', 'y', 'th_00']])
    coord[:, :2] = (coord[:, :2] - coord[:1, :2]) @ rot_mat(-dir_init).T
    coord[:, 2] -= dir_init
    coord[:, 2] = reduce_to_pi(coord[:, 2])
    return coord


def bout_features(bout, columns, filter_len=3, n_first_tail=2):
    """ For a bout returns the features

    :param bout:
    :param columns:
    :param filter_len:
    :return:
    """
    angles = pd.Series(angle_mean(bout[columns[:n_first_tail]].values+
                                  np.pi)).rolling(filter_len,
                                                  center=True,
                                                  min_periods=1).mean()
    coords = np.column_stack(
        [bout[par].rolling(filter_len, center=True, min_periods=1).mean() for par in
         ['x', 'y']]+[angles])

    # get the tail angles as raw feature
    thetas = bout[columns[0]].values
    all_angles = bout[columns].values - thetas[:, None]

    return (smooth_tail_angles_series(reduce_to_pi(all_angles[:, 1:])),
            coordinates_to_velocities(coords))


def coordinates_to_velocities(coords):
    """ Coordinates to velocities

    :param coords: time x (x, y, theta) coordinates
    :return: time x (vel_axial, vel_lateral, vel_angular)
    """
    vx = np.diff(coords[:, 0])
    vy = np.diff(coords[:, 1])

    vel_axial = np.sum(cossin(coords[:-1, 2]) * np.vstack([vx, vy]), 0)
    vel_lateral = np.sum(
        cossin(coords[:-1, 2] + np.pi / 2) * np.vstack([vx, vy]), 0)

    vel_radial = np.diff(coords[:, 2])

    return np.pad(np.column_stack([vel_axial, vel_lateral, vel_radial]),
                   ((1, 0), (0, 0)), mode='constant')


def velocities_to_coordinates(velocities, cumulative_angle=False, start_angle=0):
    """

    :param velocities: axial, lateral and angular velocities
    :param cumulative_angle: of the angle is velocity or cumulative
    :return: x, y and theta coordinates
    """

    theta = start_angle + (np.cumsum(velocities[:, 2]) if not cumulative_angle
                           else velocities[:, 2])

    x = np.cumsum(velocities[:, 0] * np.cos(theta) + \
                  velocities[:, 1] * np.cos(theta + np.pi / 2))
    y = np.cumsum(velocities[:, 0] * np.sin(theta) + \
                  velocities[:, 1] * np.sin(theta + np.pi / 2))

    return np.column_stack([x, y, theta])


def feature_history(features, history_legnth):
    """ For tensor of dimensions [n_bouts, n_timesteps, n_tail_features]
    make a tensor with a history of these parameters

    :param features:
    :param history_length:
    :return:
    """
    repeated_features = np.zeros(features.shape + (history_legnth,),
                                 dtype=features.dtype)

    n_time = features.shape[-2]
    for i in range(history_legnth):
        repeated_features[:, i:, :, i] = features[:, :n_time-i, :]

    return repeated_features
