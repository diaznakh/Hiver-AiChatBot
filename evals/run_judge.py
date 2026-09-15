from __future__ import annotations

import argparse
import json
import os
import random
import hashlib
import time
import urllib.error
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
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": "Evaluate the supplied candidate reply and return the requested JSON rating."}],
        }
    ).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read())
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace').replace(key, '[REDACTED]')[:2000]
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                delay = 20 * (attempt + 1)
                print(f'Judge HTTP {exc.code}; retrying in {delay}s.', flush=True)
                time.sleep(delay)
                continue
            raise RuntimeError(f'Judge HTTP {exc.code}: {detail}\nSaved ratings are preserved. For quota errors, wait for quota reset; no billing upgrade is required.') from None
    return json.loads(payload["choices"][0]["message"]["content"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Blindly judge saved system outputs")
    parser.add_argument("--examples", required=True)
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--split", choices=["all", "dev", "test"], default="test")
    parser.add_argument("--seed", type=int, default=20260912)
    parser.add_argument("--example-count", type=int, default=20)
    parser.add_argument("--resume", action="store_true")
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
    saved = {}
    if args.resume and output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            identifier = item['output_id']
            if identifier in saved:
                raise ValueError('Duplicate saved judge output; preserve file for diagnosis.')
            if (item.get('model'), item.get('seed'), item.get('rubric_version')) != (os.environ['JUDGE_MODEL_ID'], args.seed, 'v2'):
                raise ValueError('Saved judge model/seed/rubric differs; do not mix evaluation runs.')
            saved[identifier] = item
    expected = {blinded_output_id(row['output_id'], args.seed) for row in rows}
    if not set(saved) <= expected:
        raise ValueError('Saved judge IDs differ from this evaluation sample.')
    # Validate every saved record before appending any new result.
    for row in rows:
        identifier = blinded_output_id(row['output_id'], args.seed)
        if identifier in saved:
            evidence = [repository.get_case(cid).__dict__ for cid in row['prediction'].get('evidence_ids', [])]
            digest = hashlib.sha256(build_prompt(examples[row['example_id']], row['prediction'], evidence).encode()).hexdigest()
            if saved[identifier].get('prompt_sha256') != digest:
                raise ValueError('Saved prompt fingerprint missing or changed; preserve file and use a new output path.')
            validate_rating(saved[identifier]['rating'], {case['case_id'] for case in evidence})
    with output.open("a" if args.resume else "x") as handle:
        for row in rows:
            identifier = blinded_output_id(row['output_id'], args.seed)
            if identifier in saved:
                continue
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
            handle.write(json.dumps({"output_id": identifier, "rating": rating, "model": os.environ["JUDGE_MODEL_ID"], "rubric_version": "v2", "seed": args.seed, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}) + "\n")
            handle.flush()
            saved[identifier] = True
            print(f'Rated {len(saved)}/{len(rows)}', flush=True)
    print(f"wrote {len(rows)} blinded judge ratings to {output}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as exc:
        raise SystemExit(str(exc)) from None
