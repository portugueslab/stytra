import unittest

from stytra.tracking.fish import FishTrackingMethod
import numpy as np


class TestCentroidTracking(unittest.TestCase):
    def test_centroid_tracking(self):
        im = np.zeros((5, 5), dtype=np.uint8)
        im[1:4, 1:4] = 2
        fish_pos = FishTrackingMethod.detect(im, 1, 1)
        np.testing.assert_equal(fish_pos, (2.0, 2.0, 0.0))
