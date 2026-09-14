from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import os
import json
import re
import time
import zipfile
from xml.etree import ElementTree
from pathlib import Path

from support_agent.classifier import NaiveBayesIntentClassifier
from support_agent.factory import build_agent
from support_agent.retrieval import BM25Repository

from .baselines import run_b0, run_b1, run_b2
from .metrics import compute


def _items(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def normalize_source_id(value: str) -> str:
    # Excel may serialize integral IDs as decimals or scientific notation.
    # Preserve nonnumeric IDs and non-integral values for the source audit.
    if len(value) > 80 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value):
        return value
    try:
        number = Decimal(value)
        if number.is_finite() and number == number.to_integral_value() and number.adjusted() < 80:
            return str(int(number))
    except InvalidOperation:
        pass
    return value


def _xlsx_rows(path: Path, sheet_name: str = "Golden Set") -> list[dict[str, str]]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall(f"{{{main_ns}}}sheets/{{{main_ns}}}sheet")
        sheet = next((node for node in sheets if node.attrib["name"] == sheet_name), None)
        if sheet is None:
            required = {"example_id", "conversation_id", "message", "split",
                        "correct_intent", "correct_route", "good_reply_should_mention",
                        "reply_must_not_claim", "reviewer_name", "human_reviewed"}
            candidates = []
            headers = {}
            for node in sheets:
                name = node.attrib["name"]
                rows = _xlsx_rows(path, name)
                headers[name] = list(rows[0]) if rows else []
                if rows and required <= set(rows[0]):
                    candidates.append((name, rows))
            if len(candidates) != 1:
                raise ValueError(
                    f"Expected one data worksheet with golden-set columns; found {len(candidates)}. "
                    f"Available worksheets and headers: {headers}"
                )
            return candidates[0][1]
        relation_id = sheet.attrib[f"{{{office_rel}}}id"]
        relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            node.attrib["Target"] for node in relations.findall(f"{{{rel_ns}}}Relationship")
            if node.attrib["Id"] == relation_id
        ).lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in strings.findall(f"{{{main_ns}}}si")]
        worksheet = ElementTree.fromstring(archive.read(target))
        matrix: list[dict[int, str]] = []
        for row in worksheet.findall(f".//{{{main_ns}}}row"):
            values: dict[int, str] = {}
            for cell in row.findall(f"{{{main_ns}}}c"):
                letters = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                column = 0
                for letter in letters:
                    column = column * 26 + ord(letter) - 64
                value_node = cell.find(f"{{{main_ns}}}v")
                value = "" if value_node is None or value_node.text is None else value_node.text
                if cell.attrib.get("t") == "s" and value:
                    value = shared[int(value)]
                elif cell.attrib.get("t") == "inlineStr":
                    inline = cell.find(f"{{{main_ns}}}is")
                    value = "" if inline is None else "".join(inline.itertext())
                values[column - 1] = value
            matrix.append(values)
    if not matrix or not matrix[0]:
        return []
    headers = [matrix[0].get(index, "") for index in range(max(matrix[0]) + 1)]
    rows = [
        {header: row.get(index, "") for index, header in enumerate(headers) if header}
        for row in matrix[1:]
        if row
    ]
    for row in rows:
        for field in ("conversation_id", "target_tweet_id"):
            if field in row:
                row[field] = normalize_source_id(row[field])
    return rows


def load_examples(path: str | Path, split: str = "all") -> list[dict]:
    source = Path(path)
    if source.suffix.lower() == ".xlsx":
        raw_rows = _xlsx_rows(source)
    elif source.suffix.lower() == ".csv":
        with source.open(newline="", encoding="utf-8-sig") as handle:
            raw_rows = list(csv.DictReader(handle))
    else:
        raw_rows = None
    if raw_rows is not None:
        examples = [
            {
                "example_id": row["example_id"],
                "conversation_id": row["conversation_id"],
                "message": row["message"],
                "split": row["split"],
                "labels": {
                    "primary_intent": row["correct_intent"].strip() or None,
                    "expected_route": row["correct_route"].strip() or None,
                    "acceptable_points": _items(row["good_reply_should_mention"]),
                    "forbidden_claims": _items(row["reply_must_not_claim"]),
                },
                "annotation": {
                    "annotator_id": row["reviewer_name"].strip() or None,
                    "reviewed": row["human_reviewed"].strip().upper() == "YES",
                },
                "metadata": {"synthetic": False, "weak_labels": False},
            }
            for row in raw_rows
        ]
    else:
        examples = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    return [row for row in examples if split == "all" or row.get("split") == split]



INTENTS = {"account_prime", "delivery_tracking", "digital_service", "order_change",
           "other_unclear", "payment_charge", "product_issue", "return_refund"}


def validate_reviewed_examples(examples: list[dict]) -> None:
    if not examples:
        raise ValueError("no reviewed examples found")
    for row in examples:
        labels = row.get("labels", {})
        annotation = row.get("annotation", {})
        if (labels.get("primary_intent") not in INTENTS
                or labels.get("expected_route") not in {"AUTO_HANDLE", "ESCALATE"}
                or not labels.get("acceptable_points")
                or "forbidden_claims" not in labels
                or not annotation.get("annotator_id")
                or annotation.get("reviewed") is not True):
            raise ValueError("examples require valid labels, reply points, reviewer name and human review")
        if row.get("metadata", {}).get("synthetic") or row.get("metadata", {}).get("weak_labels"):
            raise ValueError("reviewed evaluation cannot use synthetic or weak-labelled examples")
    for field in ("example_id", "conversation_id"):
        values = [row.get(field) for row in examples]
        if any(not value for value in values) or len(values) != len(set(values)):
            raise ValueError(f"examples require distinct nonempty {field} values")


def validate_evaluation(examples: list[dict], mode: str, split: str) -> None:
    if mode == "diagnostic":
        if not examples:
            raise ValueError("no examples found")
        return
    expected_split = "dev" if mode == "development" else "test"
    if split != expected_split or any(row.get("split") != expected_split for row in examples):
        raise ValueError(f"{mode} mode requires only the {expected_split} split")
    validate_reviewed_examples(examples)
    if mode == "official" and not 150 <= len(examples) <= 250:
        raise ValueError("official mode requires 150-250 reviewed test examples")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B0/B1/B2 on an identical labelled split")
    parser.add_argument("--input", default="data/sample/real_weak_diagnostic.jsonl")
    parser.add_argument("--output", default="artifacts/latest")
    parser.add_argument("--systems", default="b0,b1,b2")
    parser.add_argument("--mode", choices=["diagnostic", "development", "official"], default="diagnostic")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    args = parser.parse_args()
    examples = load_examples(args.input, args.split)
    validate_evaluation(examples, args.mode, args.split)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    classifier = NaiveBayesIntentClassifier.load("data/indexes/intent_model.json")
    repository = BM25Repository.from_jsonl("data/indexes/support_cases.jsonl", "AmazonHelp")
    agent = build_agent(".")
    runners = {
        "b0": lambda example: run_b0(example),
        "b1": lambda example: run_b1(example, classifier, repository),
        "b2": lambda example: run_b2(example, agent),
    }
    all_metrics = {}
    for system in args.systems.split(","):
        rows = []
        for example in examples:
            started = time.perf_counter()
            prediction = runners[system](example)
            prediction["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
            rows.append({"output_id": f"{example['example_id']}::{system}", "example_id": example["example_id"], "conversation_id": example["conversation_id"], "customer_message": example["message"], "system_id": system, "gold": example["labels"], "prediction": prediction})
        with (out / f"predictions_{system}.jsonl").open("w") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        all_metrics[system] = compute(rows)
    manifest = {
        "mode": args.mode,
        "input": args.input,
        "input_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(Path("configs/app.json").read_bytes()).hexdigest(),
        "gateway": os.getenv("SUPPORT_AGENT_GATEWAY", "offline"),
        "split": args.split,
        "systems": list(all_metrics),
        "examples": len(examples),
        "warning": {
            "diagnostic": "Diagnostic results are not assignment results; labels may be heuristic.",
            "development": "Reviewed development data used for tuning; not held-out test results. See data/ANNOTATION_STATUS.md.",
            "official": None,
        }[args.mode],
    }
    (out / "metrics.json").write_text(json.dumps(all_metrics, indent=2) + "\n")
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": manifest, "metrics": all_metrics}, indent=2))


if __name__ == "__main__":
    main()
