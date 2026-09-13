from __future__ import annotations

from collections import Counter


def weighted_kappa(a: list[int], b: list[int], minimum: int = 1, maximum: int = 5) -> float | None:
    if len(a) != len(b) or not a:
        return None
    levels = list(range(minimum, maximum + 1))
    n = len(a)
    observed = Counter(zip(a, b))
    left = Counter(a)
    right = Counter(b)
    denom = (maximum - minimum) ** 2
    observed_disagreement = sum(((i - j) ** 2 / denom) * observed[i, j] / n for i in levels for j in levels)
    expected_disagreement = sum(
        ((i - j) ** 2 / denom) * (left[i] / n) * (right[j] / n) for i in levels for j in levels
    )
    if expected_disagreement == 0:
        return None
    return 1 - observed_disagreement / expected_disagreement


def binary_kappa(a: list[bool], b: list[bool]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / len(a)
    pa = sum(a) / len(a)
    pb = sum(b) / len(b)
    expected = pa * pb + (1 - pa) * (1 - pb)
    return None if expected == 1 else (observed - expected) / (1 - expected)

