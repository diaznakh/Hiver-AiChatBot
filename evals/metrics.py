from __future__ import annotations

from collections import Counter
import math
import statistics


def macro_f1(gold: list[str], predicted: list[str]) -> tuple[float, dict[str, dict[str, float | int]]]:
    # Fixed taxonomy keeps the denominator identical across baseline systems.
    labels = sorted({"account_prime", "delivery_tracking", "digital_service", "order_change",
                     "other_unclear", "payment_charge", "product_issue", "return_refund"})
    details = {}
    values = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, predicted))
        fp = sum(g != label and p == label for g, p in zip(gold, predicted))
        fn = sum(g == label and p != label for g, p in zip(gold, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        values.append(f1)
        details[label] = {
            "support": sum(g == label for g in gold),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    return (sum(values) / len(values) if values else 0.0), details


def compute(rows: list[dict]) -> dict:
    gold_intents = [row["gold"]["primary_intent"] for row in rows]
    pred_intents = [row["prediction"]["intent"] for row in rows]
    score, per_intent = macro_f1(gold_intents, pred_intents)
    n = len(rows)
    auto = [row for row in rows if row["prediction"]["route"] == "AUTO_HANDLE"]
    unsafe = [row for row in auto if row["gold"]["expected_route"] == "ESCALATE"]
    gold_escalate = [row for row in rows if row["gold"]["expected_route"] == "ESCALATE"]
    correct_escalate = [row for row in gold_escalate if row["prediction"]["route"] == "ESCALATE"]
    latencies = sorted(row["prediction"].get("latency_ms", 0.0) for row in rows)

    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        index = min(len(values) - 1, math.ceil(fraction * len(values)) - 1)
        return round(values[index], 3)

    answerable = [row for row in rows if row["gold"].get("answerable_from_index") is True]
    hits = [
        row for row in answerable
        if set(row["gold"].get("evidence_case_ids", [])) & set(row["prediction"].get("evidence_ids", []))
    ]
    return {
        "examples": n,
        "intent_macro_f1": round(score, 6),
        "intent_accuracy": round(sum(g == p for g, p in zip(gold_intents, pred_intents)) / n, 6) if n else None,
        "per_intent": per_intent,
        "auto_coverage": round(len(auto) / n, 6) if n else None,
        "auto_count": len(auto),
        "unsafe_auto_count_routing_label": len(unsafe),
        "unsafe_auto_rate_routing_label": round(len(unsafe) / len(auto), 6) if auto else None,
        "safe_auto_precision_routing_label": round((len(auto) - len(unsafe)) / len(auto), 6) if auto else None,
        "zero_event_one_sided_95pct_upper_bound": (
            round(1 - 0.05 ** (1 / len(auto)), 6) if auto and not unsafe else None
        ),
        "escalation_recall": round(len(correct_escalate) / len(gold_escalate), 6) if gold_escalate else None,
        "evidence_hit_at_5": round(len(hits) / len(answerable), 6) if answerable else None,
        "evidence_hit_denominator": len(answerable),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 3) if latencies else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
        },
        "route_confusion": {
            f"gold={gold_route}|pred={pred_route}": count
            for (gold_route, pred_route), count in Counter(
                (row["gold"]["expected_route"], row["prediction"]["route"]) for row in rows
            ).items()
        },
        "reply_quality": "PENDING_HUMAN_AND_JUDGE_RATINGS",
    }
