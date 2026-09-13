# Finish the submission

## What changed after the audit

- Offline replies now depend on supported actions in the retrieved response AND the customer topic. No supported action means an honest handoff, not a falsely grounded fixed template.
- This is a deliberately narrow, evidence-conditioned rule system, not an LLM generator. Retrieval and action-pattern matches can still be wrong. Current policy and account status remain unavailable.
- B0 is explicitly a constant-intent baseline, not an alleged majority estimator. Macro-F1 uses all eight labels consistently across systems; unsupported test classes score zero.
- Human and LLM raters receive the same fully anchored 1–5 rubric and the same acceptable/forbidden answer points.
- Rating validation rejects blanks, invalid booleans, duplicate IDs, and partial human/judge overlap. Agreement includes kappa, raw agreement, MAE, and per-system human/judge quality summaries.
- Report generation groups observed failures and includes human-rated reply failures. It cannot honestly invent five distinct modes if fewer are observed.
- Tests no longer require golden labels to remain empty after you complete them.

## Required work only you can supply

1. Open data/golden_set.xlsx. Independently label all 200 rows (50 dev, 150 test) using its Method tab. Enter your name and YES only after real review. The workbook was deliberately left untouched.
2. Run the commands below. Inspect calibration's coverage and denominators; a tiny safe sample does not establish safety.
3. Blind-rate the resulting 60 replies before viewing the judge output. Configure a compatible judge endpoint locally; never send API secrets in chat or commit them.
4. Run agreement and final report commands in README. Review the measured failure groups and write the top five actual root causes with representative examples. Merge measured sections into REPORT.md, keep the report concise, and remove pending claims only when supported.

```bash
bash scripts/reproduce.sh
python3 -m evals.calibrate --dev data/golden_set.xlsx
bash scripts/evaluate.sh
```

The remaining README commands create the blind rating sheet, call the judge,
save agreement.json and create REPORT_RESULTS.md. The judge refuses to overwrite
an existing rating file; keep successful runs and use a new output path if retrying.

No judge endpoint, model, or key was configured in the build environment, so no
live judge results are included. No human labels or agreement evidence are fabricated.

## Reproducibility caveats

- The bundled diagnostic set has heuristic labels, not ground truth. Never copy its numbers into headline results.
- Sampling is 70% non-challenge pool and 30% challenge pool, not 70% natural traffic.
- The offline action allowlist covers tracking checks, delivery-location/neighbour checks, restarts and updates. This trades coverage for auditability; unsupported intents still classify but generally hand off.
- Evidence ID validation does not prove semantic entailment. Blind reply review remains required, especially if enabling the optional live drafting adapter.
- A reviewer can reproduce the local metric computation quickly once YOUR labels and saved ratings are included. Building those labels is preparation work, not part of a claimed three-second evaluation.
- In the refreshed 100-example WEAK-LABEL diagnostic, B2 auto-handles only 1 example. This is evidence of very low provisional coverage, not trustworthy safety performance (0 unsafe out of 1 is inconclusive). Improving coverage remains an empirical task after human review.
- HLD.md and LLD.md are design references, not evidence that every proposed production feature exists. No deployment or sending service is required by the assignment.
