from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agreement import binary_kappa, weighted_kappa


def main() -> None:
    from .ratings import load, DIMENSIONS, FLAGS, summarize
    from .blinding import blinded_output_id
    parser = argparse.ArgumentParser(description="Measure judge agreement with blind human ratings")
    parser.add_argument("--human", required=True)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--output", default="artifacts/ratings/agreement.json")
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args()
    human, judge = load(args.human), load(args.judge)
    ids = sorted(set(human) & set(judge))
    if not ids or set(human) != set(judge):
        raise ValueError("human and judge IDs must match exactly; partial agreement is not accepted")
    result = {"outputs": len(ids), "ordinal_weighted_kappa": {}, "binary_kappa": {}}
    for dimension in ("groundedness", "relevance", "helpfulness", "tone"):
        result["ordinal_weighted_kappa"][dimension] = weighted_kappa(
            [human[i][dimension] for i in ids], [judge[i][dimension] for i in ids]
        )
    for flag in ("privacy_violation", "unsupported_action_claim", "unsafe_instruction", "critical_hallucination"):
        result["binary_kappa"][flag] = binary_kappa(
            [human[i][flag] for i in ids], [judge[i][flag] for i in ids]
        )
    result["raw_agreement"] = {d: sum(human[i][d] == judge[i][d] for i in ids) / len(ids) for d in (*DIMENSIONS, *FLAGS)}
    result["mean_absolute_error"] = {d: sum(abs(human[i][d] - judge[i][d]) for i in ids) / len(ids) for d in DIMENSIONS}
    result["notes"] = "Null kappa means undefined (constant ratings), not perfect agreement. Outputs from the same customer are correlated."
    mapping = {}
    for path in args.predictions:
        for line in Path(path).read_text().splitlines():
            row = json.loads(line)
            mapping[blinded_output_id(row["output_id"], args.seed)] = row["system_id"]
    if not set(ids) <= set(mapping):
        raise ValueError("ratings do not match the supplied predictions and seed")
    result["by_system"] = {system: {source: summarize([ratings[i] for i in ids if mapping[i] == system])
                                      for source, ratings in (("human", human), ("judge", judge))}
                           for system in sorted({mapping[i] for i in ids})}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
