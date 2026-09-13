#!/usr/bin/env bash
set -euo pipefail

task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"

if command -v python3 >/dev/null 2>&1; then
  task_python="python3"
elif command -v python >/dev/null 2>&1; then
  task_python="python"
else
  echo "Python 3.11 or newer is required. On macOS: brew install python" >&2
  exit 1
fi

"$task_python" -m pipeline.train_classifier \
  --input data/labels/train_weak.jsonl \
  --output data/indexes/intent_model.json

"$task_python" -m evals.run \
  --mode official \
  --input data/golden_set.xlsx \
  --split test \
  --systems b0,b1,b2 \
  --output artifacts/official

"$task_python" -m evals.report \
  --run-dir artifacts/official \
  --output artifacts/official/REPORT_RESULTS.md
