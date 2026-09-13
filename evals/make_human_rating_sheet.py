from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from support_agent.retrieval import BM25Repository

from .blinding import blinded_output_id
from .run import load_examples


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a blind human-rating sheet")
    parser.add_argument("--examples", required=True)
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="test")
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument("--example-count", type=int, default=20)
    args = parser.parse_args()
    examples = {row["example_id"]: row for row in load_examples(args.examples, args.split)}
    rows = [json.loads(line) for path in args.predictions for line in Path(path).read_text().splitlines() if line.strip()]
    rng = random.Random(args.seed)
    selected_ids = set(rng.sample(sorted(examples), min(args.example_count, len(examples))))
    rows = [row for row in rows if row["example_id"] in selected_ids]
    rng.shuffle(rows)
    repository = BM25Repository.from_jsonl("data/indexes/support_cases.jsonl", "AmazonHelp")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "output_id", "example_id", "customer_message", "candidate_reply", "retrieved_evidence",
        "acceptable_points", "forbidden_claims",
        "groundedness", "relevance", "helpfulness", "tone", "privacy_violation",
        "unsupported_action_claim", "unsafe_instruction", "critical_hallucination",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            evidence = []
            for case_id in row["prediction"].get("evidence_ids", []):
                try:
                    case = repository.get_case(case_id)
                    evidence.append({"case_id": case.case_id, "problem": case.problem_excerpt, "response": case.response_excerpt})
                except KeyError:
                    pass
            writer.writerow({
                "output_id": blinded_output_id(row["output_id"], args.seed),
                "example_id": row["example_id"],
                "customer_message": examples[row["example_id"]]["message"],
                "candidate_reply": row["prediction"]["draft"],
                "acceptable_points": json.dumps(examples[row["example_id"]]["labels"].get("acceptable_points", [])),
                "forbidden_claims": json.dumps(examples[row["example_id"]]["labels"].get("forbidden_claims", [])),
                "retrieved_evidence": json.dumps(evidence, ensure_ascii=False),
            })
    print(f"wrote {len(rows)} shuffled rating rows to {args.output}")


if __name__ == "__main__":
    main()
