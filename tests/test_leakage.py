import unittest

from pipeline.leakage import assert_no_leakage


class LeakageTests(unittest.TestCase):
    def test_leakage_check_rejects_shared_conversation(self) -> None:
        partitions = {
            "train": [{"conversation_id": "c1", "target_tweet_id": "t1", "history_tweet_ids": []}],
            "dev": [{"conversation_id": "c1", "target_tweet_id": "t2", "history_tweet_ids": []}],
            "test": [],
        }
        with self.assertRaisesRegex(AssertionError, "conversation leakage"):
            assert_no_leakage(partitions, [])

    def test_leakage_check_accepts_disjoint_data(self) -> None:
        partitions = {
            "train": [{"conversation_id": "c1", "target_tweet_id": "t1", "history_tweet_ids": []}],
            "dev": [{"conversation_id": "c2", "target_tweet_id": "t2", "history_tweet_ids": []}],
            "test": [{"conversation_id": "c3", "target_tweet_id": "t3", "history_tweet_ids": []}],
        }
        assert_no_leakage(partitions, [{"source_tweet_ids": ["t1", "brand1"]}])


if __name__ == "__main__":
    unittest.main()
