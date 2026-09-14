# Finish the submission

## Completed development review

Zaid has completed the 50 development rows in the revised uploaded workbook.
Do not repeat those rows. The revised workbook is imported and passed the source-field and label audit. See data/ANNOTATION_STATUS.md.

## Engineering workflow

1. The revised workbook is already at data/golden_set.xlsx; preserve its completed dev labels.
2. Run `bash scripts/develop.sh`. It trains the classifier, runs tests, calibrates
   on dev only, and writes development predictions, metrics and input hashes.
3. Inspect artifacts/development/calibration.json. Zero automatic coverage is a
   failed search for useful thresholds, not successful safety calibration.
4. Freeze the selected implementation and configuration before the test run.
5. After the test labels are complete, run `bash scripts/evaluate.sh`.
6. Use the README commands to generate the 60-output blinded rating sheet.
7. After human ratings, run the configured judge, score agreement, and generate
   REPORT_RESULTS.md. Incorporate actual measured failures into REPORT.md.

## Human input still required

- Label the 150 held-out test rows using the Method tab.
- Rate the 60 blinded replies before inspecting judge ratings.

A compatible judge endpoint and model must also be configured locally. No live
judge results are available yet. Keep API credentials out of committed files.

## Limits of the current prototype

- Offline guidance uses a narrow allowlist conditioned on historical replies and
  customer symptoms. It does not know current policy or account status.
- Handoffs explain that human support needs to review the request; they do not
  claim that a check or an actual handoff has happened.
- Software-update matching excludes phrases such as "keep us updated."
- Feature questions do not receive restart/update advice merely because a
  retrieved response contains those words.
- The saved artifacts/latest run is an older weak-label diagnostic. It predates
  these changes and must not be used as current development or final results.
- HLD.md and LLD.md describe proposed production features; they are not evidence
  that all such features exist. The prototype does not send customer messages.

## Verification status

The added GitHub Actions workflow runs compilation and the offline test suite.
The evaluated commit passed all 33 tests. Development metrics are recorded in
artifacts/development/REVIEW.md. No final test evaluation, judge agreement, or
successful threshold calibration is claimed.
