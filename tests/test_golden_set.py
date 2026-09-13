import csv
import json
import unittest
from pathlib import Path

from evals.run import load_examples


class GoldenSetTests(unittest.TestCase):
    def test_spreadsheet_contains_200_distinct_examples(self) -> None:
        rows = load_examples("data/golden_set.xlsx")
        self.assertEqual(len(rows), 200)
        self.assertEqual(sum(row["split"] == "dev" for row in rows), 50)
        self.assertEqual(sum(row["split"] == "test" for row in rows), 150)
        self.assertEqual(len({row["conversation_id"] for row in rows}), 200)

    def test_golden_tweet_ids_are_absent_from_training_index(self) -> None:
        with Path("data/golden_set.csv").open(newline="", encoding="utf-8") as handle:
            golden = list(csv.DictReader(handle))
        protected = {row["target_tweet_id"] for row in golden} | {
            tweet_id
            for row in golden
            for tweet_id in row["history_tweet_ids"].split("|")
            if tweet_id
        }
        index = [json.loads(line) for line in Path("data/indexes/support_cases.jsonl").read_text().splitlines()]
        indexed = {tweet_id for row in index for tweet_id in row["source_tweet_ids"]}
        self.assertFalse(protected & indexed)

    def test_customer_product_name_is_not_redacted_as_a_person(self) -> None:
        rows = load_examples("data/golden_set.xlsx")
        message = next(row["message"] for row in rows if row["example_id"] == "amazon_test_001")
        self.assertIn("Music, Video, & Books", message)


if __name__ == "__main__":
    unittest.main()
