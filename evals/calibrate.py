from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path

from support_agent.classifier import NaiveBayesIntentClassifier
from support_agent.contracts import AgentRequest
from support_agent.guardrails import GuardrailEngine
from support_agent.model_gateway import DeterministicDraftGateway
from support_agent.orchestrator import SupportOrchestrator
from support_agent.retrieval import BM25Repository

from .run import load_examples, validate_reviewed_examples


def validate_reviewed(rows: list[dict]) -> None:
    if not rows or any(not row.get("annotation", {}).get("reviewed") for row in rows):
        raise ValueError("every development example must be human-reviewed before calibration")
    if any(row["labels"].get("expected_route") not in {"AUTO_HANDLE", "ESCALATE"} for row in rows):
        raise ValueError("development routes are incomplete")

    if any(row.get("split") != "dev" for row in rows):
        raise ValueError("calibration requires development examples only")
    validate_reviewed_examples(rows)


def select_candidate(candidates):
    useful = [candidate for candidate in candidates if candidate[5] > 0]
    return max(useful) if useful else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate safe-auto thresholds on reviewed development data")
    parser.add_argument("--dev", default="data/golden_set.xlsx")
    parser.add_argument("--config", default="configs/app.json")
    parser.add_argument("--min-escalation-recall", type=float, default=0.95)
    parser.add_argument("--max-unsafe-auto-rate", type=float, default=0.05)
    parser.add_argument("--output", default="artifacts/development/calibration.json")
    args = parser.parse_args()
    if not (0 <= args.min_escalation_recall <= 1 and 0 <= args.max_unsafe_auto_rate <= 1):
        raise ValueError("safety constraints must be between zero and one")
    rows = load_examples(args.dev, "dev")
    validate_reviewed(rows)
    classifier = NaiveBayesIntentClassifier.load("data/indexes/intent_model.json")
    repository = BM25Repository.from_jsonl("data/indexes/support_cases.jsonl", "AmazonHelp")
    candidates = []
    for intent_threshold in [x / 100 for x in range(50, 96, 5)]:
        for evidence_threshold in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0]:
            agent = SupportOrchestrator(
                classifier,
                repository,
                GuardrailEngine(intent_threshold=intent_threshold, evidence_threshold=evidence_threshold),
                DeterministicDraftGateway(),
            )
            predictions = [agent.run(AgentRequest("AmazonHelp", row["message"])) for row in rows]
            auto = [i for i, result in enumerate(predictions) if result.route.value == "AUTO_HANDLE"]
            unsafe = [i for i in auto if rows[i]["labels"]["expected_route"] == "ESCALATE"]
            gold_escalate = [i for i, row in enumerate(rows) if row["labels"]["expected_route"] == "ESCALATE"]
            caught = [i for i in gold_escalate if predictions[i].route.value == "ESCALATE"]
            coverage = len(auto) / len(rows)
            unsafe_rate = len(unsafe) / len(auto) if auto else 0.0
            escalation_recall = len(caught) / len(gold_escalate) if gold_escalate else 1.0
            if escalation_recall >= args.min_escalation_recall and unsafe_rate <= args.max_unsafe_auto_rate:
                candidates.append((coverage, escalation_recall, -unsafe_rate, intent_threshold, evidence_threshold, len(auto), len(unsafe)))
    best = select_candidate(candidates)
    config_path = Path(args.config)
    config = json.loads(config_path.read_text())
    status = ("CALIBRATED_ON_HUMAN_REVIEWED_DEVELOPMENT_SET" if best
              else "NO_USEFUL_AUTO_THRESHOLD_FOUND")
    config["policy"].update({
        "tau_intent": best[3] if best else None,
        "tau_evidence": best[4] if best else None,
        "threshold_status": status,
        "auto_delivery_enabled": False,
    })
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    report = {
        "status": status,
        "input_sha256": hashlib.sha256(Path(args.dev).read_bytes()).hexdigest(),
        "development_examples": len(rows),
        "gold_auto_count": sum(row["labels"]["expected_route"] == "AUTO_HANDLE" for row in rows),
        "gold_escalate_count": sum(row["labels"]["expected_route"] == "ESCALATE" for row in rows),
        "candidate_pairs": 80,
        "feasible_pairs": len(candidates),
        "useful_feasible_pairs": sum(candidate[5] > 0 for candidate in candidates),
        "min_escalation_recall": args.min_escalation_recall,
        "max_unsafe_auto_rate": args.max_unsafe_auto_rate,
        "tau_intent": best[3] if best else None,
        "tau_evidence": best[4] if best else None,
        "development_coverage": best[0] if best else 0.0,
        "development_escalation_recall": best[1] if best else (
            1.0 if any(row["labels"]["expected_route"] == "ESCALATE" for row in rows) else None
        ),
        "development_auto_count": best[5] if best else 0,
        "development_unsafe_auto_count": best[6] if best else 0,
        "development_unsafe_auto_rate": -best[2] if best else None,
        "warning": ("Lock this config before the test run. Small denominators do not establish safety."
                    if best else "No useful threshold met the constraints. Automatic handling disabled; zero auto replies provide no safety evidence."),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
