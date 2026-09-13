import unittest

from evals.calibrate import validate_reviewed


class CalibrationTests(unittest.TestCase):
    def test_unreviewed_development_data_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "human-reviewed"):
            validate_reviewed([{"annotation": {"reviewed": False}, "labels": {}}])


if __name__ == "__main__":
    unittest.main()
