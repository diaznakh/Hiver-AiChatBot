# Low-level design

## Repository modules

| Module | Responsibility |
| --- | --- |
| `pipeline/extract_amazon.py` | Stream `twcs.csv`, pair messages, reconstruct roots, redact, split, deduplicate, and sample |
| `pipeline/train_classifier.py` | Fit and serialize the Naive Bayes intent model |
| `support_agent/classifier.py` | Predict intent and confidence |
| `support_agent/retrieval.py` | Load the training-only case index and run BM25 search |
| `support_agent/model_gateway.py` | Produce a bounded offline draft or call an optional live model endpoint |
| `support_agent/guardrails.py` | Pre-generation risk checks, output validation, and routing |
| `support_agent/orchestrator.py` | Execute classify, retrieve, draft, validate, and route in a fixed order |
| `support_agent/cli.py` | Terminal demo |
| `support_agent/ui.py` | Minimal browser demo of the three required outputs |
| `evals/run.py` | Load CSV/XLSX/JSONL examples and run B0, B1, and B2 |
| `evals/metrics.py` | Intent, routing, coverage, safety, and latency metrics |
| `evals/judge.py` | Blinded reply-quality rubric and validation |
| `evals/score_agreement.py` | Human-judge weighted and binary kappa |
| `evals/report.py` | Generate the measured results and failure section |

## Agent request and result

Input:

```json
{
  "brand_id": "AmazonHelp",
  "message": "My parcel says delivered but I cannot find it",
  "history": []
}
```

Output:

```json
{
  "intent": "delivery_tracking",
  "intent_confidence": 0.91,
  "draft": "A short support reply",
  "route": "ESCALATE",
  "reason_codes": ["ACCOUNT_ACTION_REQUIRED"],
  "reason": "This request needs an account check.",
  "evidence": [{"case_id": "amazon_123", "problem_excerpt": "...", "response_excerpt": "..."}],
  "delivery_status": "NOT_SENT"
}
```

## Execution sequence

1. Validate brand and message length.
2. Redact sensitive input patterns.
3. Predict one of the eight frozen intents.
4. Run deterministic risk checks.
5. Retrieve five same-intent AmazonHelp cases with BM25.
6. Draft a concise response from an intent-specific safe pattern.
7. Reject unsupported URLs, amounts, timing, completed actions, or private-data requests.
8. Apply confidence and evidence thresholds.
9. Return the draft, route, plain-language reason, and evidence.

Any classifier, retrieval, drafting, budget, or validation failure returns a neutral escalation rather than an automatic recommendation.

## Golden-set schema

`data/golden_set.xlsx` contains 200 rows. Only six fields require human input:

| Field | Rule |
| --- | --- |
| `correct_intent` | One value from the frozen eight-intent taxonomy |
| `correct_route` | `AUTO_HANDLE` or `ESCALATE` |
| `good_reply_should_mention` | One to three semantic points separated by `|` |
| `reply_must_not_claim` | Unsupported statements separated by `|`; may be blank |
| `reviewer_name` | Human reviewer name |
| `human_reviewed` | `YES` only after the row has been checked |

The loader rejects official evaluation unless 150-250 selected examples have an intent, route, at least one acceptable reply point, reviewer name, and `human_reviewed=YES`.

## Metrics

For intents, macro-F1 is the unweighted mean of the per-intent F1 values. Routing metrics are:

- `auto_coverage = predicted AUTO_HANDLE / all examples`
- `unsafe_auto_rate = gold ESCALATE but predicted AUTO_HANDLE / predicted AUTO_HANDLE`
- `safe_auto_precision = safe predicted AUTO_HANDLE / predicted AUTO_HANDLE`
- `escalation_recall = correctly escalated / gold ESCALATE`

The report always shows auto coverage next to unsafe-auto results so an always-escalate baseline cannot appear useful merely because it has zero unsafe automatic decisions.

## Reproduction

```bash
bash scripts/reproduce.sh
python3 -m support_agent.ui
```

After human labelling:

```bash
python3 -m evals.calibrate --dev data/golden_set.xlsx
bash scripts/evaluate.sh
```

The evaluation reads the workbook directly using Python's standard library. No Excel library is required on the reviewer's machine.
