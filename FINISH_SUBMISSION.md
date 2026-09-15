# Finish the submission

## Already completed

- All 200 golden rows are populated and marked reviewed.
- Original source fields pass the audit after exact spreadsheet ID normalization.
- The frozen 150-row B0/B1/B2 evaluation is saved and reproduced.
- REPORT.md contains measured results, five real failure modes and limitations.
- Predictions and the 60-output blinded rating sheet are committed.
- The local test suite passes 37 tests.
- Three optional classifier alternatives were evaluated on development only.

The agent still has 50% original test accuracy and zero automatic coverage.
The optional 54% development classifier result is not a replacement test score.

## Remaining human work

1. Read LABEL_REVIEW.md: four specific annotation concerns need your judgment.
   Keep the frozen workbook intact; record any confirmed corrections separately.
2. Fill artifacts/ratings/human_ratings.csv using evals/human_rating_guide.md.
   Enter 1–5 for four quality dimensions and TRUE/FALSE for four safety flags.
   Keep all IDs unchanged. Do not inspect predictions or judge scores first.
3. Configure JUDGE_API_URL, JUDGE_API_KEY and JUDGE_MODEL_ID locally.
   Do not put API keys in chat, source files or commits.

Once the 60 ratings are complete:

```bash
bash scripts/finish_submission.sh
```

This validates the exact rating set, calls the judge if no judge file exists,
calculates agreement and generates artifacts/official/REPORT_RESULTS.md.
It refuses incomplete human ratings and never fills them automatically.
If a judge run stops halfway, preserve the partial file for diagnosis and use
a new output path with evals.run_judge; do not treat partial agreement as complete.

Check evidence status at any time:

```bash
python3 -m evals.check_submission
```

After agreement is available, incorporate its measured reply-quality section
into REPORT.md and remove pending statements only when supported.

## Submit

Use the form linked in the assignment. Include the repository link and REPORT.md.
The brief allows a public repo or a private repo with evaluator access. This
repository remains private; verify the evaluators have access before submitting.
No submission has been sent.

The task permits AI coding assistants. Be prepared to explain the classifier,
BM25 retrieval, guardrails, leakage checks and evaluation limitations live.
