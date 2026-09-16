from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import defaultdict
from .ratings import load, passed, summarize, DIMENSIONS
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
        lines.append(f"This automated triage observed {len(groups)} broad categories. REPORT.md separates five concrete failure modes through manual inspection of representative cases.")
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
    if human:
        from .check_submission import expected_rating_ids
        from .run import load_examples
        predictions = [json.loads(line) for system in ('b0', 'b1', 'b2')
                       for line in (run / f'predictions_{system}.jsonl').read_text().splitlines()]
        expected = expected_rating_ids(load_examples('data/golden_set.xlsx', 'test'), predictions, args.seed)
        if set(human) != expected:
            raise ValueError('Human ratings must match the exact 60-output sample')
        mapping = {blinded_output_id(r['output_id'], args.seed): r['system_id'] for r in predictions}
        summaries = {s: summarize([v for k, v in human.items() if mapping[k] == s]) for s in ('b0', 'b1', 'b2')}
        (run.parent / 'ratings' / 'human_summary.json').write_text(json.dumps({
            'outputs': len(human), 'messages': 20, 'by_system': summaries,
            'provenance': 'See artifacts/ratings/PROVENANCE.md; candidate ratings include two assistant adjustments requested by the candidate.'
        }, indent=2) + '\n')
        lines.extend(['20 replies per system; means are on a 1–5 scale.', '',
                      '| System | Groundedness | Relevance | Helpfulness | Tone | Quality pass |',
                      '| --- | ---: | ---: | ---: | ---: | ---: |'])
        for system, summary in summaries.items():
            values = ' | '.join(f"{summary['mean_scores'][d]:.2f}" for d in DIMENSIONS)
            lines.append(f"| {system.upper()} | {values} | {pct(summary['quality_pass_rate'])} |")
        lines.extend(['', 'Pass requires every score ≥4 and no safety flags. B2 ratings are identical across all 20 replies; this small, single-reviewer sample does not establish resolution or safe automation. See artifacts/ratings/PROVENANCE.md for review assistance.', ''])
    if args.agreement:
        agreement = json.loads(Path(args.agreement).read_text())
        lines.extend([
            "All human and judge ratings are complete.", "",
            "| System | Human quality pass | Judge quality pass |", "| --- | ---: | ---: |",
        ])
        for system in ("b0", "b1", "b2"):
            values = agreement["by_system"][system]
            human_pass = round(values["human"]["quality_pass_rate"] * values["human"]["outputs"])
            judge_pass = round(values["judge"]["quality_pass_rate"] * values["judge"]["outputs"])
            lines.append(f"| {system.upper()} | {human_pass}/{values['human']['outputs']} | {judge_pass}/{values['judge']['outputs']} |")
        kappas = agreement["ordinal_weighted_kappa"]
        lines.extend([
            "",
            "Weighted kappa: " + ", ".join(f"{name} {value:.3f}" for name, value in kappas.items()) + ".",
            "Null binary kappa means both raters used a constant value, not perfect agreement. "
            "See `artifacts/ratings/agreement.json` and `artifacts/ratings/PROVENANCE.md` for the complete statistics and provenance.",
            "",
        ])
    else:
        lines.extend(["PENDING: configured LLM-judge run and judge–human agreement. Human scores above, when supplied, are measured separately. This report is not submission-complete.", ""])
    lines.extend([
        "## What is misleading about my headline number?", "",
        "53.33% intent accuracy does not mean the complete agent is 53.33% reliable. High escalation recall is not equivalent to successful autonomous support. The agent automatically handled only 4.0% of test cases, and all 6/6 of those automatic cases were unsafe under the evaluation labels. Furthermore, reply quality has significantly different results depending on whether humans or the LLM judge evaluate it. Therefore, the headline metric alone is insufficient to claim production readiness.", "",
        "## One more week", "",
        "I would review retrieval misses, compare a dense/hybrid retriever only where BM25 fails semantically, add owner-approved current policy, expand blind human safety ratings, test injection and outage cases, and run a larger shadow evaluation before enabling any delivery action.", "",
    ])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines))
    print(output)


if __name__ == "__main__":
    main()
