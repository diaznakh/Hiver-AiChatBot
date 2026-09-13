from __future__ import annotations

import argparse
import json
from pathlib import Path

from support_agent.classifier import NaiveBayesIntentClassifier
from support_agent.contracts import AgentRequest
from support_agent.guardrails import GuardrailEngine
from support_agent.model_gateway import DeterministicDraftGateway
from support_agent.orchestrator import SupportOrchestrator
from support_agent.retrieval import BM25Repository

from .run import load_examples


def validate_reviewed(rows: list[dict]) -> None:
    if not rows or any(not row.get("annotation", {}).get("reviewed") for row in rows):
        raise ValueError("every development example must be human-reviewed before calibration")
    if any(row["labels"].get("expected_route") not in {"AUTO_HANDLE", "ESCALATE"} for row in rows):
        raise ValueError("development routes are incomplete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate safe-auto thresholds on reviewed development data")
    parser.add_argument("--dev", default="data/golden_set.xlsx")
    parser.add_argument("--config", default="configs/app.json")
    parser.add_argument("--min-escalation-recall", type=float, default=0.95)
    parser.add_argument("--max-unsafe-auto-rate", type=float, default=0.05)
    args = parser.parse_args()
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
    if not candidates:
        raise ValueError("no threshold pair met the safety constraints; keep auto-handling disabled")
    best = max(candidates)
    config_path = Path(args.config)
    config = json.loads(config_path.read_text())
    config["policy"]["tau_intent"] = best[3]
    config["policy"]["tau_evidence"] = best[4]
    config["policy"]["threshold_status"] = "CALIBRATED_ON_HUMAN_REVIEWED_DEVELOPMENT_SET"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    print(json.dumps({
        "tau_intent": best[3], "tau_evidence": best[4], "development_coverage": best[0],
        "development_escalation_recall": best[1], "development_unsafe_auto_count": best[6],
        "development_auto_count": best[5], "warning": "Lock this config before the test run."
    }, indent=2))


if __name__ == "__main__":
    main()
