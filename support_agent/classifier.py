from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .contracts import IntentPrediction

TOKEN = re.compile(r"[\w']+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    words = TOKEN.findall(text.lower())
    bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)]
    return words + bigrams


class KeywordIntentClassifier:
    """Transparent fallback classifier used before a fitted model exists."""

    DEFAULT_KEYWORDS = {
        "delivery_issue": {"delivery", "delivered", "parcel", "package", "late", "arrive"},
        "return_refund": {"return", "refund", "refunded", "money", "collected"},
        "account_access": {"account", "login", "password", "locked", "signin"},
        "payment_issue": {"payment", "charged", "charge", "card", "billing"},
        "product_issue": {"broken", "damaged", "faulty", "product", "item", "replacement"},
    }

    def __init__(self, keywords: dict[str, set[str]] | None = None) -> None:
        self.keywords = keywords or self.DEFAULT_KEYWORDS

    def predict(self, message: str, history=()) -> IntentPrediction:
        tokens = set(tokenize(" ".join([*(getattr(x, "text", str(x)) for x in history), message])))
        scores = {label: len(words & tokens) for label, words in self.keywords.items()}
        best, best_score = max(scores.items(), key=lambda pair: pair[1])
        tied = sum(score == best_score for score in scores.values()) > 1
        if best_score == 0:
            return IntentPrediction("other_unclear", 0.0, True)
        confidence = min(0.95, 0.45 + 0.15 * best_score)
        return IntentPrediction(best, confidence, tied)


class NaiveBayesIntentClassifier:
    """Small trainable baseline with a JSON-serializable model."""

    def __init__(self) -> None:
        self.labels: list[str] = []
        self.doc_counts: Counter[str] = Counter()
        self.word_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.totals: Counter[str] = Counter()
        self.vocab: set[str] = set()

    def fit(self, examples: list[tuple[str, str]]) -> "NaiveBayesIntentClassifier":
        if not examples:
            raise ValueError("training examples are required")
        for text, label in examples:
            self.doc_counts[label] += 1
            words = tokenize(text)
            self.word_counts[label].update(words)
            self.totals[label] += len(words)
            self.vocab.update(words)
        self.labels = sorted(self.doc_counts)
        return self

    def predict(self, message: str, history=()) -> IntentPrediction:
        if not self.labels:
            raise RuntimeError("classifier has not been fitted")
        words = tokenize(" ".join([*(getattr(x, "text", str(x)) for x in history), message]))
        total_docs = sum(self.doc_counts.values())
        scores: dict[str, float] = {}
        for label in self.labels:
            score = math.log(self.doc_counts[label] / total_docs)
            denominator = self.totals[label] + len(self.vocab)
            for word in words:
                score += math.log((self.word_counts[label][word] + 1) / denominator)
            scores[label] = score
        peak = max(scores.values())
        probs = {k: math.exp(v - peak) for k, v in scores.items()}
        normalizer = sum(probs.values())
        probs = {k: v / normalizer for k, v in probs.items()}
        ordered = sorted(probs.items(), key=lambda pair: pair[1], reverse=True)
        ambiguous = len(ordered) > 1 and ordered[0][1] - ordered[1][1] < 0.10
        return IntentPrediction(ordered[0][0], round(ordered[0][1], 6), ambiguous)

    def save(self, path: str | Path) -> None:
        payload = {
            "labels": self.labels,
            "doc_counts": dict(self.doc_counts),
            "word_counts": {k: dict(v) for k, v in self.word_counts.items()},
            "totals": dict(self.totals),
            "vocab": sorted(self.vocab),
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "NaiveBayesIntentClassifier":
        data = json.loads(Path(path).read_text())
        model = cls()
        model.labels = data["labels"]
        model.doc_counts = Counter(data["doc_counts"])
        model.word_counts = defaultdict(Counter, {k: Counter(v) for k, v in data["word_counts"].items()})
        model.totals = Counter(data["totals"])
        model.vocab = set(data["vocab"])
        return model

