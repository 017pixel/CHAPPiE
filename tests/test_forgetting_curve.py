import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory.forgetting_curve import EbbinghausForgettingCurve


class ForgettingCurveTests(unittest.TestCase):
    def test_reference_points_match_ebbinghaus_profile(self):
        curve = EbbinghausForgettingCurve()

        self.assertAlmostEqual(curve.calculate_retention(20 / 60, 1.0), 0.58, delta=0.05)
        self.assertAlmostEqual(curve.calculate_retention(1.0, 1.0), 0.44, delta=0.05)
        self.assertAlmostEqual(curve.calculate_retention(24.0, 1.0), 0.33, delta=0.05)

    def test_strength_slows_decay(self):
        curve = EbbinghausForgettingCurve()

        weak = curve.calculate_retention(24.0, 1.0)
        stronger = curve.calculate_retention(24.0, 2.0)

        self.assertGreater(stronger, weak)

    def test_optimal_review_time_is_positive(self):
        curve = EbbinghausForgettingCurve()
        review_hours = curve.get_optimal_review_time(1.0, 0.7)

        self.assertGreater(review_hours, 0)


if __name__ == "__main__":
    unittest.main()