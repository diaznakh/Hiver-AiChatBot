from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BRAND = "AmazonHelp"
SEED = 20260912

INTENT_PATTERNS = {
    "return_refund": re.compile(r"\b(return(?:ed|ing)?|refund(?:ed|ing)?|reimburse|money back)\b", re.I),
    "payment_charge": re.compile(r"\b(payment|pay(?:ment)?|charged?|billing|credit card|debit card|gift card)\b", re.I),
    "account_prime": re.compile(r"\b(account|log[ -]?in|sign[ -]?in|password|prime membership|membership|subscription)\b", re.I),
    "digital_service": re.compile(r"\b(kindle|audible|prime video|amazon video|fire stick|fire tv|alexa|echo|ebook|stream|download|app)\b", re.I),
    "product_issue": re.compile(r"\b(damaged|broken|defective|faulty|wrong item|missing item|not working)\b", re.I),
    "delivery_tracking": re.compile(r"\b(deliver(?:y|ed|ing)?|package|parcel|tracking|shipment|courier|driver|arriv(?:e|ed|al|ing))\b", re.I),
    "order_change": re.compile(r"\b(order(?:ed|ing)?|cancel(?:led|ing|ation)?|pre[ -]?order|change address)\b", re.I),
}

ACCOUNT_ACTION = re.compile(
    r"\b(refund|return|cancel|charged?|payment|account|password|membership|change address|missing|stolen|delivered but)\b",
    re.I,
)
DM = re.compile(r"\b(dm|direct message|private message)\b", re.I)
ACTIONABLE = re.compile(r"\b(try|check|select|open|restart|reset|update|settings|visit|contact|call|follow|turn)\b", re.I)
URL = re.compile(r"https?://\S+", re.I)
HANDLE = re.compile(r"@[A-Za-z0-9_]{2,15}")
ORDER_ID = re.compile(r"\b\d{3}-\d{7}-\d{7}\b")
LONG_NUMBER = re.compile(r"\b\d{6,}\b")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
UK_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)
GREETING_NAME = re.compile(
    r"\b(Hi|Hello|Hey|Thanks|Apologies|Sorry)(\s+|,\s*)([A-Z][a-z]{2,})(?=[,.!?])"
)
CONTEXT_NAME = re.compile(
    r"\b(details|disappointment|frustration|concern),\s+([A-Z][a-z]{2,})(?=[,.!?])",
    re.I,
)
VOCATIVE_NAME = re.compile(r",\s+([A-Z][a-z]{2,})(?=[,.!?])")


def parse_time(raw: str) -> datetime:
    return datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize(text: str, *, redact_vocative: bool = False) -> tuple[str, list[str]]:
    value = html.unescape(text).replace("\n", " ").strip()
    flags = []
    if EMAIL.search(value) or PHONE.search(value) or UK_POSTCODE.search(value):
        value = EMAIL.sub("[EMAIL]", value)
        value = PHONE.sub("[PHONE]", value)
        value = UK_POSTCODE.sub("[POSTCODE]", value)
        flags.append("PII_REDACTED")
    if URL.search(value):
        value = URL.sub("[URL]", value)
        flags.append("URL_REDACTED")
    if HANDLE.search(value):
        value = HANDLE.sub("[HANDLE]", value)
    if GREETING_NAME.search(value) or CONTEXT_NAME.search(value) or (redact_vocative and VOCATIVE_NAME.search(value)):
        value = GREETING_NAME.sub(lambda match: f"{match.group(1)}{match.group(2)}[NAME]", value)
        value = CONTEXT_NAME.sub(lambda match: f"{match.group(1)}, [NAME]", value)
        if redact_vocative:
            value = VOCATIVE_NAME.sub(", [NAME]", value)
        flags.append("NAME_REDACTED")
    value = re.sub(r"\s*\^[A-Za-z]{1,4}\s*$", "", value).strip()
    if ORDER_ID.search(value) or LONG_NUMBER.search(value):
        value = ORDER_ID.sub("[ORDER_ID]", value)
        value = LONG_NUMBER.sub("[IDENTIFIER]", value)
        flags.append("IDENTIFIER_REDACTED")
    return " ".join(value.split()), flags


def suggest_intent(text: str) -> tuple[str, list[str]]:
    matches = [label for label, pattern in INTENT_PATTERNS.items() if pattern.search(text)]
    return (matches[0] if matches else "other_unclear"), matches


def evidence_type(response: str) -> str:
    if DM.search(response):
        return "private_channel_handoff"
    if ACTIONABLE.search(response) or "?" in response:
        return "actionable_guidance"
    return "outcome_unknown"


def root_and_history(target_id: str, rows: dict[str, dict], max_depth: int = 100) -> tuple[str, list[str], bool]:
    current = target_id
    history = []
    seen = {current}
    for _ in range(max_depth):
        parent = rows[current].get("in_response_to_tweet_id") if current in rows else None
        if not parent:
            return current, list(reversed(history)), current in rows
        if parent in seen:
            return current, list(reversed(history)), False
        if parent not in rows:
            return current, list(reversed(history)), False
        seen.add(parent)
        history.append(parent)
        current = parent
    return current, list(reversed(history)), False


def load_brand_pairs(source: Path) -> tuple[list[dict], dict]:
    brand_rows: dict[str, dict] = {}
    parent_ids: set[str] = set()
    with source.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["author_id"] == BRAND and row["inbound"] == "False":
                brand_rows[row["tweet_id"]] = row
                if row["in_response_to_tweet_id"]:
                    parent_ids.add(row["in_response_to_tweet_id"])

    customer_rows: dict[str, dict] = {}
    with source.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["tweet_id"] in parent_ids:
                customer_rows[row["tweet_id"]] = row

    relevant = {**brand_rows, **customer_rows}
    by_target: dict[str, list[dict]] = defaultdict(list)
    for brand_row in brand_rows.values():
        parent = customer_rows.get(brand_row["in_response_to_tweet_id"])
        if parent and parent["inbound"] == "True":
            by_target[parent["tweet_id"]].append(brand_row)

    cases = []
    incomplete = 0
    for target_id, responses in by_target.items():
        customer = customer_rows[target_id]
        response = min(responses, key=lambda row: parse_time(row["created_at"]))
        root, history, complete = root_and_history(target_id, relevant)
        incomplete += int(not complete)
        message, message_flags = sanitize(customer["text"])
        reply, reply_flags = sanitize(response["text"], redact_vocative=True)
        suggested_intent, matches = suggest_intent(message)
        kind = evidence_type(reply)
        flags = [*message_flags, *reply_flags]
        if kind == "private_channel_handoff":
            flags.append("PRIVATE_HANDOFF")
        if len(reply) < 45:
            flags.append("SHORT_RESPONSE")
        challenge = (
            len(matches) != 1
            or not complete
            or len(message) < 35
            or bool(ACCOUNT_ACTION.search(message))
            or sum(ord(ch) > 127 for ch in message) > max(8, len(message) // 5)
        )
        cases.append(
            {
                "conversation_id": root,
                "target_tweet_id": target_id,
                "response_tweet_id": response["tweet_id"],
                "created_at": customer["created_at"],
                "response_created_at": response["created_at"],
                "message": message,
                "observed_response": reply,
                "history_tweet_ids": history,
                "complete": complete,
                "suggested_primary_intent": suggested_intent,
                "matched_intents": matches,
                "suggested_route": "ESCALATE" if ACCOUNT_ACTION.search(message) or kind != "actionable_guidance" else "AUTO_HANDLE",
                "evidence_type": kind,
                "quality_flags": sorted(set(flags)),
                "challenge_candidate": challenge,
            }
        )
    audit = {
        "brand_id": BRAND,
        "brand_replies": len(brand_rows),
        "unique_parent_ids": len(parent_ids),
        "available_parent_rows": len(customer_rows),
        "direct_customer_brand_pairs": len(cases),
        "incomplete_ancestry_pairs": incomplete,
    }
    return cases, audit


def split_and_deduplicate(cases: list[dict]) -> tuple[dict[str, list[dict]], dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        groups[case["conversation_id"]].append(case)
    ordered_groups = sorted(groups, key=lambda group: min(parse_time(row["created_at"]) for row in groups[group]))
    first_cut, second_cut = int(len(ordered_groups) * 0.70), int(len(ordered_groups) * 0.85)
    group_split = {
        group: ("train" if i < first_cut else "dev" if i < second_cut else "test")
        for i, group in enumerate(ordered_groups)
    }
    output = {"train": [], "dev": [], "test": []}
    seen_messages = set()
    duplicates = 0
    for case in sorted(cases, key=lambda row: parse_time(row["created_at"])):
        digest = hashlib.sha256(" ".join(case["message"].lower().split()).encode()).hexdigest()
        if digest in seen_messages:
            duplicates += 1
            continue
        seen_messages.add(digest)
        case["split"] = group_split[case["conversation_id"]]
        output[case["split"]].append(case)
    return output, {"conversation_groups": len(groups), "exact_duplicate_messages_removed": duplicates}


def stratified_sample(rows: list[dict], count: int, challenge_share: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_group = {}
    for row in rows:
        by_group.setdefault(row["conversation_id"], row)
    unique = list(by_group.values())
    challenge = [row for row in unique if row["challenge_candidate"]]
    ordinary = [row for row in unique if not row["challenge_candidate"]]
    hard_n = min(round(count * challenge_share), len(challenge))
    easy_n = count - hard_n
    if len(ordinary) < easy_n or len(unique) < count:
        raise ValueError("not enough distinct cases for requested sample")
    chosen = rng.sample(challenge, hard_n) + rng.sample(ordinary, easy_n)
    rng.shuffle(chosen)
    return chosen


def label_template(row: dict, example_id: str, stratum: str) -> dict:
    return {
        "example_id": example_id,
        "conversation_id": row["conversation_id"],
        "target_tweet_id": row["target_tweet_id"],
        "history_tweet_ids": row["history_tweet_ids"],
        "message": row["message"],
        "split": row["split"],
        "sampling_stratum": stratum,
        "suggestions_not_human_labels": {
            "primary_intent": row["suggested_primary_intent"],
            "expected_route": row["suggested_route"],
            "matched_intents": row["matched_intents"],
        },
        "labels": {
            "primary_intent": None,
            "secondary_intents": [],
            "expected_route": None,
            "reason_codes": [],
            "acceptable_points": [],
            "forbidden_claims": [],
            "evidence_case_ids": [],
            "answerable_from_index": None,
            "ambiguity_note": None,
        },
        "annotation": {"annotator_id": None, "guide_version": "v1", "reviewed": False},
        "source": {"dataset": "Customer Support on Twitter", "brand_id": BRAND},
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_golden_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "example_id",
        "split",
        "sampling_stratum",
        "message",
        "correct_intent",
        "correct_route",
        "good_reply_should_mention",
        "reply_must_not_claim",
        "reviewer_name",
        "human_reviewed",
        "conversation_id",
        "target_tweet_id",
        "history_tweet_ids",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "example_id": row["example_id"],
                    "split": row["split"],
                    "sampling_stratum": row["sampling_stratum"],
                    "message": row["message"],
                    "correct_intent": "",
                    "correct_route": "",
                    "good_reply_should_mention": "",
                    "reply_must_not_claim": "",
                    "reviewer_name": "",
                    "human_reviewed": "NO",
                    "conversation_id": row["conversation_id"],
                    "target_tweet_id": row["target_tweet_id"],
                    "history_tweet_ids": "|".join(row["history_tweet_ids"]),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a real AmazonHelp submission subset")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--train-cases", type=int, default=5600)
    args = parser.parse_args()
    root = Path(args.root)
    source = Path(args.csv)
    cases, audit = load_brand_pairs(source)
    partitions, split_stats = split_and_deduplicate(cases)
    rng = random.Random(SEED)

    by_intent = defaultdict(list)
    for row in partitions["train"]:
        by_intent[row["suggested_primary_intent"]].append(row)
    per_intent = max(1, args.train_cases // len(by_intent))
    selected_train = []
    for intent in sorted(by_intent):
        pool = by_intent[intent]
        selected_train.extend(rng.sample(pool, min(per_intent, len(pool))))
    if len(selected_train) < args.train_cases:
        used = {row["target_tweet_id"] for row in selected_train}
        remainder = [row for row in partitions["train"] if row["target_tweet_id"] not in used]
        selected_train.extend(rng.sample(remainder, min(args.train_cases - len(selected_train), len(remainder))))
    rng.shuffle(selected_train)

    dev = stratified_sample(partitions["dev"], 50, 0.30, SEED + 1)
    test = stratified_sample(partitions["test"], 150, 0.30, SEED + 2)
    dev_ids = {row["target_tweet_id"] for row in dev}
    diagnostic_pool = [row for row in partitions["dev"] if row["target_tweet_id"] not in dev_ids]
    diagnostic = stratified_sample(diagnostic_pool, 100, 0.30, SEED + 3)

    index_rows = []
    train_labels = []
    for row in selected_train:
        case_id = f"amazon_{row['target_tweet_id']}"
        index_rows.append(
            {
                "case_id": case_id,
                "brand_id": BRAND,
                "problem_excerpt": row["message"][:500],
                "response_excerpt": row["observed_response"][:500],
                "source_tweet_ids": [row["target_tweet_id"], row["response_tweet_id"]],
                "source_timestamp": row["response_created_at"],
                "evidence_type": row["evidence_type"],
                "intent": row["suggested_primary_intent"],
                "score": 0.0,
                "index_version": "amazon-weak-v1",
                "quality_flags": [*row["quality_flags"], "WEAK_LABEL_REQUIRES_AUDIT"],
            }
        )
        train_labels.append({"text": row["message"], "label": row["suggested_primary_intent"], "label_source": "heuristic_weak_label"})

    golden_dev = [label_template(row, f"amazon_dev_{i:03d}", "challenge" if row["challenge_candidate"] else "random") for i, row in enumerate(dev, 1)]
    golden_test = [label_template(row, f"amazon_test_{i:03d}", "challenge" if row["challenge_candidate"] else "random") for i, row in enumerate(test, 1)]
    diagnostic_rows = []
    for i, row in enumerate(diagnostic, 1):
        diagnostic_rows.append(
            {
                "example_id": f"amazon_diagnostic_{i:03d}",
                "conversation_id": row["conversation_id"],
                "message": row["message"],
                "labels": {
                    "primary_intent": row["suggested_primary_intent"],
                    "expected_route": row["suggested_route"],
                    "acceptable_points": [],
                    "forbidden_claims": [],
                },
                "metadata": {"synthetic": False, "weak_labels": True, "not_official_evaluation": True},
            }
        )

    write_jsonl(root / "data/indexes/support_cases.jsonl", index_rows)
    write_jsonl(root / "data/labels/train_weak.jsonl", train_labels)
    write_golden_csv(root / "data/golden_set.csv", [*golden_dev, *golden_test])
    write_jsonl(root / "data/sample/real_weak_diagnostic.jsonl", diagnostic_rows)

    audit.update(split_stats)
    audit.update(
        {
            "source_file": source.name,
            "source_size_bytes": source.stat().st_size,
            "source_sha256": file_sha256(source),
            "split_method": "chronological 70/15/15 by conversation root, then global exact-text deduplication",
            "eligible_by_split": {name: len(rows) for name, rows in partitions.items()},
            "selected_training_evidence": len(index_rows),
            "training_intent_counts": Counter(row["intent"] for row in index_rows),
            "golden_set": {"total": 200, "dev": 50, "test": 150, "reviewed": False},
            "diagnostic_examples": 100,
            "status": "REAL_DATA_WITH_WEAK_TRAIN_LABELS_AND_UNREVIEWED_GOLDEN_LABELS",
            "seed": SEED,
        }
    )
    (root / "data/manifest.json").write_text(json.dumps(audit, indent=2, default=dict) + "\n")
    print(json.dumps(audit, indent=2, default=dict))


if __name__ == "__main__":
    main()
