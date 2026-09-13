from __future__ import annotations

import argparse
import json
from pathlib import Path

from support_agent.classifier import NaiveBayesIntentClassifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample/train.jsonl")
    parser.add_argument("--output", default="data/indexes/intent_model.json")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.input).read_text().splitlines() if line.strip()]
    model = NaiveBayesIntentClassifier().fit([(row["text"], row["label"]) for row in rows])
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    model.save(args.output)
    print(f"trained on {len(rows)} rows; labels={','.join(model.labels)}; output={args.output}")


if __name__ == "__main__":
    main()

