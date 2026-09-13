import unittest

from evals.agreement import binary_kappa, weighted_kappa
from evals.blinding import blinded_output_id


class AgreementTests(unittest.TestCase):
    def test_perfect_agreement(self) -> None:
        self.assertEqual(weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)
        self.assertEqual(binary_kappa([True, False, True], [True, False, True]), 1.0)

    def test_blinded_ids_do_not_expose_system_name(self) -> None:
        blinded = blinded_output_id("amazon_test_001::b2", 20260912)
        self.assertTrue(blinded.startswith("rating_"))
        self.assertNotIn("b2", blinded)
        self.assertEqual(blinded, blinded_output_id("amazon_test_001::b2", 20260912))


if __name__ == "__main__":
    unittest.main()
