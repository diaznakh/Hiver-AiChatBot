from __future__ import annotations

import argparse
import json
import os
import random
import urllib.request
from pathlib import Path

from support_agent.retrieval import BM25Repository

from .blinding import blinded_output_id
from .judge import build_prompt, validate_rating
from .run import load_examples


def call_judge(prompt: str) -> dict:
    url = os.environ["JUDGE_API_URL"]
    key = os.environ["JUDGE_API_KEY"]
    model = os.environ["JUDGE_MODEL_ID"]
    body = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": prompt}],
        }
    ).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read())
    return json.loads(payload["choices"][0]["message"]["content"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Blindly judge saved system outputs")
    parser.add_argument("--examples", required=True)
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="test")
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument("--example-count", type=int, default=20)
    args = parser.parse_args()
    missing = [name for name in ("JUDGE_API_URL", "JUDGE_API_KEY", "JUDGE_MODEL_ID") if not os.getenv(name)]
    if missing:
        parser.error("Configure " + ", ".join(missing) + "; keep API keys out of source control.")
    examples = {row["example_id"]: row for row in load_examples(args.examples, args.split)}
    rows = [json.loads(line) for path in args.predictions for line in Path(path).read_text().splitlines() if line.strip()]
    rng = random.Random(args.seed)
    selected_ids = set(rng.sample(sorted(examples), min(args.example_count, len(examples))))
    rows = [row for row in rows if row["example_id"] in selected_ids]
    rng.shuffle(rows)
    repository = BM25Repository.from_jsonl("data/indexes/support_cases.jsonl", "AmazonHelp")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        for row in rows:
            evidence = []
            for case_id in row["prediction"].get("evidence_ids", []):
                try:
                    evidence.append(repository.get_case(case_id).__dict__)
                except KeyError:
                    pass
            prompt = build_prompt(examples[row["example_id"]], row["prediction"], evidence)
            rating = call_judge(prompt)
            allowed_ids = {case["case_id"] for case in evidence}
            validate_rating(rating, allowed_ids)
            handle.write(json.dumps({"output_id": blinded_output_id(row["output_id"], args.seed), "rating": rating, "model": os.environ["JUDGE_MODEL_ID"], "rubric_version": "v2", "seed": args.seed}) + "\n")
            handle.flush()
    print(f"wrote {len(rows)} blinded judge ratings to {output}")


if __name__ == "__main__":
    main()
