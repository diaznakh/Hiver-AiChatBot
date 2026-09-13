import json
import unittest

from support_agent.retrieval import BM25Repository


class RetrievalTests(unittest.TestCase):
    def test_bm25_is_brand_scoped_and_validates_limit(self) -> None:
        repo = BM25Repository.from_jsonl("data/indexes/support_cases.jsonl", "AmazonHelp")
        cases = repo.search("late parcel tracking", "delivery_tracking", 3)
        self.assertTrue(cases)
        self.assertTrue(all(case.brand_id == "AmazonHelp" for case in cases))
        self.assertTrue(all(case.intent == "delivery_tracking" for case in cases))
        with self.assertRaises(ValueError):
            repo.search("anything", limit=6)

    def test_real_index_weak_labels_are_visibly_non_official(self) -> None:
        with open("data/indexes/support_cases.jsonl") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        self.assertTrue(rows)
        self.assertTrue(all(row["case_id"].startswith("amazon_") for row in rows))
        self.assertTrue(all("WEAK_LABEL_REQUIRES_AUDIT" in row["quality_flags"] for row in rows))


if __name__ == "__main__":
    unittest.main()
