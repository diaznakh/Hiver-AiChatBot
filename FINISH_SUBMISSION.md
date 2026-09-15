# Finish the submission

## Already completed

- All 200 golden rows are populated and marked reviewed.
- Original source fields pass the audit after exact spreadsheet ID normalization.
- The frozen 150-row B0/B1/B2 evaluation is saved and reproduced.
- REPORT.md contains measured results, five real failure modes and limitations.
- Predictions and all 60 completed reply ratings are committed.
- Human quality summaries and assisted-review provenance are included.
- The local test suite passes 37 tests.
- Three optional classifier alternatives were evaluated on development only.

The agent still has 50% original test accuracy and zero automatic coverage.
The optional 54% development classifier result is not a replacement test score.

## Remaining human work

The four concerns now have an AI-reviewed supplement and a reproducible score
comparison in LABEL_REVIEW.md. Original human labels remain the official results.

Configure a compatible judge locally using the interactive command below.
It asks for the HTTPS chat-completions endpoint, model ID and a hidden API key;
credentials are passed to the process and are not written to files.

```bash
git pull --ff-only
python3 scripts/finish_with_judge.py
```

This is the only remaining evaluation step that needs access unavailable to
the assistant. The provider receives the sampled messages/replies/evidence
and may charge API usage. Do not paste your API key into chat.

The 60 ratings are already complete. Once the judge is configured:

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
