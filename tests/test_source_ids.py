import unittest
from evals.run import normalize_source_id


class SourceIdTests(unittest.TestCase):
    def test_integral_spreadsheet_formats(self):
        for value in ("123", "123.0", "1.23E+2"):
            self.assertEqual(normalize_source_id(value), "123")

    def test_changed_values_are_not_rounded(self):
        self.assertEqual(normalize_source_id("123.4"), "123.4")
        self.assertEqual(normalize_source_id("124.0"), "124")

    def test_composite_ids_preserved(self):
        self.assertEqual(normalize_source_id("amazon_dev_001"), "amazon_dev_001")
        self.assertEqual(normalize_source_id("123|456"), "123|456")
