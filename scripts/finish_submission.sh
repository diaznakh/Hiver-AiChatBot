#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
python3 -m evals.check_submission --stage human
python3 -m evals.run_judge --resume --examples data/golden_set.xlsx \
    --predictions artifacts/official/predictions_b0.jsonl artifacts/official/predictions_b1.jsonl artifacts/official/predictions_b2.jsonl \
    --output artifacts/ratings/judge_ratings.jsonl
python3 -m evals.score_agreement --human artifacts/ratings/human_ratings.csv \
  --judge artifacts/ratings/judge_ratings.jsonl \
  --predictions artifacts/official/predictions_b0.jsonl artifacts/official/predictions_b1.jsonl artifacts/official/predictions_b2.jsonl
python3 -m evals.report --run-dir artifacts/official \
  --human-ratings artifacts/ratings/human_ratings.csv --agreement artifacts/ratings/agreement.json
python3 -m evals.check_submission
