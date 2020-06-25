import numpy as np
from stytra.tracking.online_bouts import find_bouts_online, BoutState


def test_online_bout_det():
    vel_profile = np.array([0, 2, 3, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]).astype(
        np.float64
    )
    coords = np.zeros((len(vel_profile), 3))
    k, _, _ = find_bouts_online(
        vel_profile,
        coords,
        BoutState(0, 0.0, 0, 0, 0),
        [coords[0]],
        threshold=1,
        pad_after=1,
        pad_before=0,
    )
    assert len(k) == 11
