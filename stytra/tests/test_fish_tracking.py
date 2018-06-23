from stytra.tracking.fish import find_fish_simple
import numpy as np


def test_centroid_tracking():
    im = np.zeros((5,5), dtype=np.uint8)
    im[1:4, 1:4] = 2
    assert find_fish_simple(im, 1) == (2.0, 2.0)