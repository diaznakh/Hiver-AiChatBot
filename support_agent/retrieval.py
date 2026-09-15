from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from .classifier import tokenize
from .contracts import EvidenceCase


class BM25Repository:
    def __init__(self, cases: list[EvidenceCase], *, brand_id: str, index_version: str) -> None:
        self.cases = [case for case in cases if case.brand_id == brand_id]
        self.brand_id = brand_id
        self.index_version = index_version
        self.documents = [tokenize(c.problem_excerpt) for c in self.cases]
        self.avgdl = sum(map(len, self.documents)) / len(self.documents) if self.documents else 0.0
        self.df = Counter(word for doc in map(set, self.documents) for word in doc)

    @classmethod
    def from_jsonl(cls, path: str | Path, brand_id: str) -> "BM25Repository":
        cases = []
        index_version = "unknown"
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            index_version = row.get("index_version", index_version)
            row["source_tweet_ids"] = tuple(row.get("source_tweet_ids", []))
            row["quality_flags"] = tuple(row.get("quality_flags", []))
            cases.append(EvidenceCase(**row))
        return cls(cases, brand_id=brand_id, index_version=index_version)

    def search(self, query: str, intent: str | None = None, limit: int = 5) -> list[EvidenceCase]:
        if not 1 <= limit <= 5:
            raise ValueError("limit must be between 1 and 5")
        if len(query) > 1_000:
            raise ValueError("query exceeds 1,000 characters")
        if not self.documents:
            return []
        q = tokenize(query)
        scored: list[tuple[float, EvidenceCase]] = []
        n = len(self.documents)
        for case, doc in zip(self.cases, self.documents):
            tf = Counter(doc)
            score = 0.0
            for term in q:
                if not tf[term]:
                    continue
                idf = math.log(1 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
                numerator = tf[term] * 2.5
                denominator = tf[term] + 1.5 * (1 - 0.75 + 0.75 * len(doc) / self.avgdl)
                score += idf * numerator / denominator
            # Soft intent boost: prefer same-intent cases but don't exclude others
            if intent and case.intent == intent:
                score *= 1.5
            if score > 0:
                scored.append((score, case))
        scored.sort(key=lambda pair: (-pair[0], pair[1].case_id))
        return [EvidenceCase(**{**case.__dict__, "score": round(score, 6)}) for score, case in scored[:limit]]

    def get_case(self, case_id: str) -> EvidenceCase:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)

