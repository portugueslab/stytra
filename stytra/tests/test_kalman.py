import numpy as np
from stytra.tracking.simple_kalman import NewtonianKalman


def test_simple_kalman():
    """ Tests the NewtonianKalman filter, compared to the reference
    implementation in filterpy

    """
    kn = NewtonianKalman(0, 1.0, 0.02, 0.1)
    kn.predict()
    kn.update(1.0)
    np.testing.assert_allclose(kn.x, np.array([0.66666667, 0.33333347]))
