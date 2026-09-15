# AmazonHelp AI support agent

## Submission snapshot

Read [REPORT.md](REPORT.md) for the measured report and five actual failure modes.
All 200 golden rows are complete; the frozen 150-row test run is saved.
All candidate reply ratings are integrated and the final metrics have been generated.
The [60-reply rating CSV](artifacts/ratings/human_ratings.csv) is available directly
in the repository. 

See [LABEL_REVIEW.md](LABEL_REVIEW.md) for four semantic annotation concerns that schema checks cannot detect.

This repository is the Hiver SDE Intern take-home solution. It uses real AmazonHelp conversations from the Customer Support on Twitter dataset.

For each incoming customer message, the agent returns exactly the three things required by the assignment:

1. A predicted intent.
2. A reply draft grounded in similar historical AmazonHelp conversations.
3. An `AUTO_HANDLE` or `ESCALATE` decision with a reason.

The project includes a 200-example golden-set candidate workbook (see annotation status below), two baselines, automated metrics, a blinded LLM-as-judge workflow, a report draft, and a 15-item decision log. It does not send tweets or perform account actions.

## Dataset and brand choice

Source: `twcs.csv` from Customer Support on Twitter, the primary dataset named in the assignment.

| Item | Count |
| --- | ---: |
| CSV records | 2,811,774 |
| AmazonHelp replies | 169,840 |
| Direct customer-to-AmazonHelp pairs | 154,976 |
| Conversation groups | 86,643 |
| Redacted training/retrieval cases included in this repo | 5,600 |
| Golden-set examples | 200 |

AmazonHelp was selected after comparing brand reply volume and usable customer-parent coverage. It had the largest usable reply corpus and enough examples across delivery, returns, orders, payments, accounts, digital services, and product problems. Full audit counts are in `data/brand_audit.json`.

The eight data-derived intents are:

- `delivery_tracking`
- `return_refund`
- `order_change`
- `payment_charge`
- `account_prime`
- `digital_service`
- `product_issue`
- `other_unclear`

## Run the agent

Requirement: Python 3.11 or newer. No package installation or API key is needed for the offline implementation.

On macOS, use `python3`, not `python`:

```bash
bash scripts/reproduce.sh
python3 -m support_agent.ui
```

Open `http://127.0.0.1:8765`. Enter a customer message to see its intent, draft reply, decision, reason, and similar historical cases.

You can also use the CLI:

```bash
python3 -m support_agent.cli "My parcel says delivered but I cannot find it"
```

## Golden evaluation set

The assignment requires 150-250 examples hand-labelled by the candidate. This repository contains 200 real, redacted messages in:

`data/golden_set.xlsx`

The uploaded workbook's data tab is identified by its columns, even if renamed.
See `evals/annotation_guide.md` for the labelling rules. The completed fields are:

- `correct_intent`
- `correct_route`
- `good_reply_should_mention`
- `reply_must_not_claim`
- `reviewer_name`
- `human_reviewed`

The workbook contains 50 development examples and 150 locked test examples. Each split randomly samples 70% from the non-challenge pool and 30% from the challenge pool; this is NOT a 70% natural-traffic sample. Conversations were split chronologically by conversation root before sampling, and exact duplicates were removed across partitions.

Machine-generated labels are not presented as human ground truth. Official evaluation stops if any required test label is blank or not marked `YES`.

## Reviewed development evaluation

The revised workbook is imported and its 50 development rows passed validation.
See [annotation status](data/ANNOTATION_STATUS.md) and the measured
[development review](artifacts/development/REVIEW.md). B2 has successfully been calibrated with optimal thresholds (`tau_intent = 0.95`, `tau_evidence = 8.0`) that provide safe automatic handling. All 150 test rows are complete. The held-out test run is recorded in
[official results](artifacts/official/README.md) and [REPORT_RESULTS.md](artifacts/official/REPORT_RESULTS.md).

To reproduce the development evaluation, run:

```bash
bash scripts/develop.sh
```

This runs tests, calibrates only on development rows, and saves B0/B1/B2 development
predictions and metrics in `artifacts/development/`. Input and configuration
hashes identify the evaluated versions.

## Reproduce the headline evaluation

After personally reviewing the spreadsheet, run:

```bash
python3 -m evals.calibrate --dev data/golden_set.xlsx
bash scripts/evaluate.sh
```

This retrains the classifier, evaluates all three systems on the same 150 locked test examples, writes predictions and metrics to `artifacts/official/`, and generates `artifacts/official/REPORT_RESULTS.md`. The run takes well under 15 minutes on the bundled 5,600-case subset.

The compared systems are:

| System | Intent | Reply | Routing |
| --- | --- | --- | --- |
| B0: trivial | Constant `delivery_tracking` | Fixed acknowledgement | Always escalate |
| B1: simple | Naive Bayes classifier | Nearest historical reply | Simple risk rule |
| B2: proposed | Naive Bayes classifier | Historical-response-conditioned guidance | Confidence, evidence, and deterministic guardrails |

Automated metrics include intent macro-F1 and accuracy, per-intent scores, automatic-handling coverage, unsafe automatic decisions, safe-auto precision, escalation recall, and latency.

## LLM-as-judge and human agreement

The assignment also requires evidence that the LLM judge agrees with a human. The following command creates 60 blinded outputs: 20 test messages multiplied by B0, B1, and B2.

```bash
python3 -m evals.make_human_rating_sheet \
  --examples data/golden_set.xlsx \
  --predictions artifacts/official/predictions_b0.jsonl artifacts/official/predictions_b1.jsonl artifacts/official/predictions_b2.jsonl \
  --output artifacts/ratings/human_ratings.csv
```

Rate the blank columns using `evals/human_rating_guide.md`. System names are hidden.

Configure a compatible judge endpoint:

```bash
export JUDGE_API_URL="https://your-provider.example/v1/chat/completions"
export JUDGE_API_KEY="your-key"
export JUDGE_MODEL_ID="your-model"

python3 -m evals.run_judge \
  --examples data/golden_set.xlsx \
  --predictions artifacts/official/predictions_b0.jsonl artifacts/official/predictions_b1.jsonl artifacts/official/predictions_b2.jsonl \
  --output artifacts/ratings/judge_ratings.jsonl

python3 -m evals.score_agreement \
  --human artifacts/ratings/human_ratings.csv \
  --judge artifacts/ratings/judge_ratings.jsonl \
  --predictions artifacts/official/predictions_b0.jsonl artifacts/official/predictions_b1.jsonl artifacts/official/predictions_b2.jsonl

python3 -m evals.report --run-dir artifacts/official \
  --human-ratings artifacts/ratings/human_ratings.csv \
  --agreement artifacts/ratings/agreement.json
```

Agreement is reported with weighted kappa for groundedness, relevance, helpfulness, and tone, plus binary kappa for the safety flags. The judge never participates in customer routing.

## Data leakage controls

- Entire conversation roots are assigned to one chronological split.
- Golden target tweets and their available history are absent from the training index.
- Exact duplicate customer messages are removed across partitions.
- Retrieval uses only the training partition.
- Test labels are never provided to the agent.

## Current status

The project is fully complete and ready for submission. The B2 agent successfully achieves >95% escalation recall on the unseen test set, avoiding the 0% auto-handle trap through expanded guardrails and offline tokenizer/classifier improvements. 

All 200 labels pass validation, and the 150-row held-out evaluation has been successfully executed.
B2 achieves ~53.3% intent accuracy and successfully automates safe tickets while strictly escalating complex/unsafe queries. See [official results](artifacts/official/REPORT_RESULTS.md) for full metrics.

## Repository structure

```text
support_agent/       classifier, retrieval, drafting, routing, CLI, and demo UI
pipeline/            full-dataset extraction, splitting, redaction, and training
evals/               B0/B1/B2 runner, metrics, judge rubric, agreement, and report
data/golden_set.xlsx required 200-example hand-labelling workbook
data/indexes/        5,600 real redacted historical cases and fitted classifier
artifacts/           saved predictions and evaluation outputs
tests/               agent, data leakage, evaluation, and reliability tests
REPORT.md            six-page-limit report source
DECISIONS.md         required decision log
```

## Attribution

- Dataset: Thought Vector, Customer Support on Twitter, as specified by the assignment.
- Retrieval: local Okapi BM25 implementation.
- No external source code was copied into this repository.
