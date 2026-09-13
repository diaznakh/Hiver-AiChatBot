import csv
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.prepare_dataset import export_brand, ingest


class PipelineTests(unittest.TestCase):
    def test_ingest_and_brand_export_preserve_group_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "twcs.csv"
            fields = [
                "tweet_id", "author_id", "inbound", "created_at", "text",
                "response_tweet_id", "in_response_to_tweet_id",
            ]
            rows = [
                ["1", "customer", "True", "Tue Oct 31 22:10:47 +0000 2017", "late parcel", "2", ""],
                ["2", "AmazonHelp", "False", "Tue Oct 31 22:11:47 +0000 2017", "sorry", "", "1"],
                ["3", "customer", "True", "Tue Oct 31 22:12:47 +0000 2017", "still late", "4", "2"],
                ["4", "AmazonHelp", "False", "Tue Oct 31 22:13:47 +0000 2017", "review", "", "3"],
            ]
            with source.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                writer.writerows(rows)
            db = root / "work.sqlite3"
            stats = ingest(source, db)
            self.assertEqual(stats["accepted"], 4)
            manifest = export_brand(db, "AmazonHelp", root / "processed", root / "manifest.json")
            self.assertEqual(manifest["conversation_groups"], 1)
            exported = []
            for path in (root / "processed").glob("*.jsonl"):
                exported.extend(json.loads(line) for line in path.read_text().splitlines() if line)
            second = next(row for row in exported if row["target_tweet_id"] == "3")
            self.assertEqual(second["conversation_id"], "1")
            self.assertEqual(second["history_tweet_ids"], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
