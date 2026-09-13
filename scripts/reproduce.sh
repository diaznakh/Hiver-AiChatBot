#!/usr/bin/env bash
set -euo pipefail

task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_root"

if command -v python3 >/dev/null 2>&1; then
  task_python="python3"
elif command -v python >/dev/null 2>&1; then
  task_python="python"
else
  echo "Python 3.11 or newer is required. Install it with: brew install python" >&2
  exit 1
fi

"$task_python" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"Python 3.11+ is required; found {sys.version.split()[0]}")
PY

"$task_python" -m pipeline.train_classifier --input data/labels/train_weak.jsonl --output data/indexes/intent_model.json
"$task_python" -m unittest discover -s tests -v
"$task_python" -m evals.run --mode diagnostic --output artifacts/latest
"$task_python" -m support_agent.cli "My parcel is late and tracking has not moved"
