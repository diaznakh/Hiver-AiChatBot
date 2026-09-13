from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import defaultdict
from .ratings import load, passed
from .blinding import blinded_output_id


def pct(value) -> str:
    return "N/A" if value is None else f"{100 * value:.1f}%"


def failure_description(row: dict) -> tuple[str, str]:
    gold = row["gold"]
    prediction = row["prediction"]
    if gold["expected_route"] == "ESCALATE" and prediction["route"] == "AUTO_HANDLE":
        return "Unsafe automatic routing", "The risk rules or confidence threshold missed an account-specific or ambiguous request."
    if gold["expected_route"] == "AUTO_HANDLE" and prediction["route"] == "ESCALATE":
        return "Over-escalation", "The safety gate was too conservative or the retrieved evidence was too weak."
    if gold["primary_intent"] != prediction["intent"]:
        return "Intent misclassification", "Weak training labels, overlapping intents, or limited language coverage likely caused the error."
    if not prediction.get("evidence_ids"):
        return "No usable historical evidence", "Lexical retrieval did not find a sufficiently relevant training case."
    return "Reply or evidence mismatch", "The draft did not satisfy the labelled response requirements despite retrieving a case."


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the measured-results report section")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", default="artifacts/official/REPORT_RESULTS.md")
    parser.add_argument("--human-ratings")
    parser.add_argument("--agreement")
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args()
    run = Path(args.run_dir)
    manifest = json.loads((run / "run_manifest.json").read_text())
    if manifest.get("mode") != "official":
        raise ValueError("refusing to generate a submission report from non-official results")
    metrics = json.loads((run / "metrics.json").read_text())
    b2_rows = [json.loads(line) for line in (run / "predictions_b2.jsonl").read_text().splitlines()]
    human = load(args.human_ratings) if args.human_ratings else {}
    failures = [
        row for row in b2_rows
        if row["gold"]["primary_intent"] != row["prediction"]["intent"]
        or row["gold"]["expected_route"] != row["prediction"]["route"]
        or (blinded_output_id(row["output_id"], args.seed) in human
            and not passed(human[blinded_output_id(row["output_id"], args.seed)]))
    ]
    groups = defaultdict(list)
    for row in failures:
        groups[failure_description(row)[0]].append(row)
    lines = [
        "# Measured results - AmazonHelp support agent", "",
        "## Results", "",
        "| System | Intent macro-F1 | Auto coverage | Unsafe auto | Escalation recall |", "| --- | ---: | ---: | ---: | ---: |",
    ]
    for system in ("b0", "b1", "b2"):
        value = metrics[system]
        unsafe = f"{value['unsafe_auto_count_routing_label']}/{value['auto_count']}" if value["auto_count"] else "N/A (0 auto)"
        lines.append(f"| {system.upper()} | {value['intent_macro_f1']:.3f} | {pct(value['auto_coverage'])} | {unsafe} | {pct(value['escalation_recall'])} |")
    lines.extend(["", "## Observed failure categories and representative examples", "",
                  "Routing/intent failures use the full test split; reply-only failures use the human-rated subset. Counts are not directly comparable across these denominators. Categories are automated triage, not a substitute for inspecting root causes.", ""])
    if len(groups) < 5:
        lines.append(f"Only {len(groups)} categories observed by this harness. Inspect examples for finer root causes; do not invent five modes.")
    for number, (category, members) in enumerate(sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:5], 1):
        row = members[0]
        mode, hypothesis = failure_description(row)
        lines.extend([
            f"### {number}. {mode} ({len(members)} observed) - {row['example_id']}", "",
            f"Customer: {row.get('customer_message', '[Read from locked example by ID]')}", "",
            f"Expected: intent `{row['gold']['primary_intent']}`, route `{row['gold']['expected_route']}`.", "",
            f"Predicted: intent `{row['prediction']['intent']}`, route `{row['prediction']['route']}`; reasons `{', '.join(row['prediction']['reason_codes'])}`.", "",
            f"Draft: {row['prediction']['draft']}", "",
            f"Retrieved evidence IDs: {', '.join(row['prediction'].get('evidence_ids', [])) or 'none'}.", "",
            f"Hypothesis: {hypothesis}", "",
        ])
    lines.extend(["## Reply quality and judge-human agreement", ""])
    if args.agreement:
        agreement = json.loads(Path(args.agreement).read_text())
        lines.extend(["```json", json.dumps(agreement, indent=2), "```", ""])
    else:
        lines.extend(["PENDING: supply --agreement and --human-ratings after blind review. This report is not submission-complete.", ""])
    lines.extend([
        "## What is misleading about my headline number?", "",
        "Macro-F1 gives every intent equal weight but does not describe reply quality or routing safety. Coverage must be shown beside unsafe-auto outcomes because an always-escalate system can appear safe while doing no useful automatic work. The challenge slice is deliberately oversampled, so its mixed score is not a natural-traffic estimate. Historical Twitter replies are behavior evidence, not current policy. A zero unsafe count is not proof of zero risk; report its exact denominator and one-sided bound.", "",
        "## One more week", "",
        "I would review retrieval misses, compare a dense/hybrid retriever only where BM25 fails semantically, add owner-approved current policy, expand blind human safety ratings, test injection and outage cases, and run a larger shadow evaluation before enabling any delivery action.", "",
    ])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))
    print(output)


if __name__ == "__main__":
    main()
