import numpy as np
from stytra.tracking.simple_kalman import NewtonianKalman
from stytra.tracking.fish import Fish, IndexBooking


def test_simple_kalman():
    """ Tests the NewtonianKalman filter, compared to the reference
    implementation in filterpy

    """
    kn = NewtonianKalman(0, 1.0, 0.02, 0.1)
    kn.predict()
    kn.update(1.0)
    np.testing.assert_allclose(kn.x, np.array([0.66666667, 0.33333347]))


def test_fish():
    """ Test fish Kalman updating with angle correction

    Returns
    -------

    """
    ib = IndexBooking(1)
    f = Fish(np.array([0.0, 0.0, np.pi + 0.1]), ib)
    f.predict()
    f.update([1.0, 1.0, np.pi + 2 * np.pi])
    assert np.allclose(
        f.serialize(),
        np.array(
            [[0.66666667, 0.33333466, 0.66666667, 0.33333466, 3.17492599, -0.03333376]]
        ),
    )

    f = Fish(np.array([0.0, 0.0, np.pi + 0.1]), ib)
    f.predict()
    f.update([1.0, 1.0, -np.pi - 2 * np.pi])
    assert np.allclose(
        f.serialize(),
        np.array(
            [[0.66666667, 0.33333466, 0.66666667, 0.33333466, 3.17492599, -0.03333376]]
        ),
    )
