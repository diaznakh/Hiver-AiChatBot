"""Check submission evidence without filling missing human or judge ratings."""
import argparse
import hashlib
import json
import random
from pathlib import Path

from .blinding import blinded_output_id
from .ratings import load
from .run import load_examples, validate_evaluation


def expected_rating_ids(examples, prediction_rows, seed=20260912):
    selected = set(random.Random(seed).sample(sorted(row['example_id'] for row in examples), 20))
    expected = {blinded_output_id(row['output_id'], seed) for row in prediction_rows if row['example_id'] in selected}
    if len(expected) != 60:
        raise ValueError('Expected 60 unique blinded outputs from 20 test messages and three systems')
    return expected


def require_complete_ratings(path, expected):
    ratings = load(path)
    if set(ratings) != expected:
        raise ValueError('Rating IDs must match all 60 expected outputs exactly')
    return ratings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['human', 'complete'], default='complete')
    args = parser.parse_args()
    root = Path('artifacts/official')
    examples = load_examples('data/golden_set.xlsx', 'test')
    validate_evaluation(examples, 'official', 'test')
    manifest = json.loads((root / 'run_manifest.json').read_text())
    if manifest['input_sha256'] != hashlib.sha256(Path('data/golden_set.xlsx').read_bytes()).hexdigest():
        raise ValueError('Workbook differs from the frozen run; do not silently reuse predictions')
    rows = [json.loads(line) for system in ('b0', 'b1', 'b2')
            for line in (root / f'predictions_{system}.jsonl').read_text().splitlines()]
    expected = expected_rating_ids(examples, rows)
    required = ['human_ratings.csv']
    if args.stage == 'complete':
        required.append('judge_ratings.jsonl')
    pending = []
    for name in required:
        try:
            require_complete_ratings(Path('artifacts/ratings') / name, expected)
        except (OSError, ValueError, KeyError) as exc:
            pending.append({'file': name, 'reason': str(exc)})
    if args.stage == 'complete' and not Path('artifacts/ratings/agreement.json').exists():
        pending.append({'file': 'agreement.json', 'reason': 'Run scripts/finish_submission.sh after completing ratings'})
    result = {'test_rows': len(examples), 'expected_reply_ratings': len(expected),
              'pending': pending, 'status': 'PENDING_EVIDENCE' if pending else 'EVIDENCE_PRESENT',
              'note': 'This verifies evidence completeness, not label correctness or production readiness. See LABEL_REVIEW.md.'}
    output = Path('artifacts/submission_status.json')
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if pending else 0)


if __name__ == '__main__':
    main()
