import numpy as np
from stytra.tracking.fish import Fishes


def test_fish():
    """ Test fish Kalman updating with angle correction

    Returns
    -------

    """
    fshs = Fishes(1, 1.0, 1.0, 2, 1.0, 1)
    fshs.add_fish(np.array([0.0, 0.0, np.pi + 0.1, 0.0, 0.0]))
    fshs.predict()
    fshs.update(np.array([1.0, 1.0, np.pi + 2 * np.pi, 0.0, 0.0]))
    assert np.allclose(
        fshs.coords,
        np.array(
            [
                [
                    0.66666667,
                    0.33333466,
                    0.66666667,
                    0.33333466,
                    3.17492599,
                    -0.03333376,
                    0.0,
                    0.0,
                ]
            ]
        ),
    )
