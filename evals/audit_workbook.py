"""Audit the workbook against the original source rows without changing labels."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from .run import _xlsx_rows, load_examples, validate_reviewed_examples


def main():
    source = Path("data/golden_set.xlsx")
    raw = _xlsx_rows(source)
    with Path("data/golden_set.csv").open(newline="", encoding="utf-8-sig") as handle:
        original = list(csv.DictReader(handle))
    by_id = {row["example_id"]: row for row in original}
    if len(raw) != 200 or len({row["example_id"] for row in raw}) != 200:
        raise ValueError("Expected 200 distinct examples")
    if {row["example_id"] for row in raw} != set(by_id):
        raise ValueError("Example IDs differ from the source set")
    immutable = ("conversation_id", "message", "split", "target_tweet_id", "history_tweet_ids")
    for row in raw:
        for field in immutable:
            if row[field] != by_id[row["example_id"]][field]:
                raise ValueError(f"Source field changed: {row['example_id']} {field}")
    dev = load_examples(source, "dev")
    test = load_examples(source, "test")
    if len(dev) != 50 or len(test) != 150:
        raise ValueError("Expected 50 dev and 150 test examples")
    validate_reviewed_examples(dev)
    complete_test = []
    for row in test:
        try:
            validate_reviewed_examples([row])
            complete_test.append(row)
        except ValueError:
            pass
    missing = {}
    test_raw = [row for row in raw if row["split"] == "test"]
    for field in ("correct_intent", "correct_route", "good_reply_should_mention",
                  "reviewer_name", "human_reviewed"):
        missing[field] = sum(not row.get(field, "").strip() for row in test_raw)
    report = {
        "test_blank_fields": missing,
        "test_review_flags": dict(Counter(row.get("human_reviewed", "") for row in test_raw)),
        "test_invalid_intents": sum(bool(row["labels"]["primary_intent"]) and row["labels"]["primary_intent"] not in {
            "account_prime", "delivery_tracking", "digital_service", "order_change",
            "other_unclear", "payment_charge", "product_issue", "return_refund"} for row in test),
        "test_invalid_routes": sum(bool(row["labels"]["expected_route"]) and row["labels"]["expected_route"] not in {
            "AUTO_HANDLE", "ESCALATE"} for row in test),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_fields_unchanged": True,
        "development_rows": len(dev),
        "development_routes": dict(Counter(row["labels"]["expected_route"] for row in dev)),
        "reviewers": sorted({row["annotation"]["annotator_id"] for row in dev}),
        "test_rows": len(test),
        "complete_test_rows": len(complete_test),
        "pending_test_rows": len(test) - len(complete_test),
    }
    output = Path("artifacts/development")
    output.mkdir(parents=True, exist_ok=True)
    (output / "workbook_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    with (output / "golden_set.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    print("WORKBOOK_AUDIT_JSON=" + json.dumps(report))


if __name__ == "__main__":
    main()
