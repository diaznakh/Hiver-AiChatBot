from __future__ import annotations

import argparse
import csv
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


def _xlsx_rows(path: Path, sheet_name: str = "Golden Set") -> list[dict[str, str]]:
    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            node for node in workbook.findall(f"{{{main_ns}}}sheets/{{{main_ns}}}sheet")
            if node.attrib["name"] == sheet_name
        )
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
    headers = [matrix[0].get(index, "") for index in range(max(matrix[0]) + 1)]
    return [
        {header: row.get(index, "") for index, header in enumerate(headers) if header}
        for row in matrix[1:]
        if row
    ]


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B0/B1/B2 on an identical labelled split")
    parser.add_argument("--input", default="data/sample/real_weak_diagnostic.jsonl")
    parser.add_argument("--output", default="artifacts/latest")
    parser.add_argument("--systems", default="b0,b1,b2")
    parser.add_argument("--mode", choices=["diagnostic", "official"], default="diagnostic")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    args = parser.parse_args()
    examples = load_examples(args.input, args.split)
    if args.mode == "official":
        if not 150 <= len(examples) <= 250 or any(
            row.get("metadata", {}).get("synthetic") or row.get("metadata", {}).get("weak_labels")
            for row in examples
        ):
            raise ValueError("official mode requires 150-250 non-synthetic, human-labelled examples")
        required = {"primary_intent", "expected_route", "acceptable_points", "forbidden_claims"}
        if any(not required <= set(row.get("labels", {})) for row in examples):
            raise ValueError("official examples have incomplete labels")
        if any(
            row["labels"].get("primary_intent") is None
            or row["labels"].get("expected_route") is None
            or not row["labels"].get("acceptable_points")
            or not row.get("annotation", {}).get("annotator_id")
            or not row.get("annotation", {}).get("reviewed", False)
            for row in examples
        ):
            raise ValueError("official examples must be reviewed by a human")
        intents = {"account_prime", "delivery_tracking", "digital_service", "order_change",
                   "other_unclear", "payment_charge", "product_issue", "return_refund"}
        if any(row["labels"]["primary_intent"] not in intents or row["labels"]["expected_route"] not in {"AUTO_HANDLE", "ESCALATE"} for row in examples):
            raise ValueError("invalid golden intent or route; use the documented taxonomy")
        groups = [row.get("conversation_id") for row in examples]
        if None in groups or len(groups) != len(set(groups)):
            raise ValueError("official examples must use distinct conversation groups")
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
        "split": args.split,
        "systems": list(all_metrics),
        "examples": len(examples),
        "warning": "Real tweets with heuristic weak labels; diagnostic results are not assignment results." if args.mode == "diagnostic" else None,
    }
    (out / "metrics.json").write_text(json.dumps(all_metrics, indent=2) + "\n")
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"manifest": manifest, "metrics": all_metrics}, indent=2))


if __name__ == "__main__":
    main()
