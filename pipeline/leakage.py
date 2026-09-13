from __future__ import annotations

import json
from pathlib import Path


def load(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def assert_no_leakage(partitions: dict[str, list[dict]], evidence: list[dict]) -> None:
    group_sets = {name: {row["conversation_id"] for row in rows} for name, rows in partitions.items()}
    tweet_sets = {
        name: {row["target_tweet_id"] for row in rows} | {tid for row in rows for tid in row.get("history_tweet_ids", [])}
        for name, rows in partitions.items()
    }
    names = sorted(partitions)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            if group_sets[left] & group_sets[right]:
                raise AssertionError(f"conversation leakage: {left}/{right}")
            if tweet_sets[left] & tweet_sets[right]:
                raise AssertionError(f"tweet leakage: {left}/{right}")
    evidence_ids = {tid for case in evidence for tid in case.get("source_tweet_ids", [])}
    protected = tweet_sets.get("dev", set()) | tweet_sets.get("test", set())
    if evidence_ids & protected:
        raise AssertionError("golden target/history tweet appears in retrieval index")

