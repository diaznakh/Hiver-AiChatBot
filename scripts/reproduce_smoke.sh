#!/usr/bin/env bash
# Compatibility entrypoint for the original macOS instructions.
set -euo pipefail
task_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$task_root/scripts/reproduce.sh" "$@"
