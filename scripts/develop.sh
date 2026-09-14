#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"
python3 -m pipeline.train_classifier --input data/labels/train_weak.jsonl --output data/indexes/intent_model.json
python3 -m unittest discover -s tests -v
python3 -m evals.calibrate --dev data/golden_set.xlsx
python3 -m evals.run --mode development --input data/golden_set.xlsx --split dev --output artifacts/development
