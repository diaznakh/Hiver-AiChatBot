"""Score an explicitly post-test label supplement without changing frozen files."""
import copy
import json
from pathlib import Path
from .metrics import compute


def main():
    review = json.loads(Path('data/labels/review_supplement.json').read_text())
    changes = {row['example_id']: row for row in review['changes']}
    results = {}
    for system in ('b0', 'b1', 'b2'):
        original = [json.loads(line) for line in Path(f'artifacts/official/predictions_{system}.jsonl').read_text().splitlines()]
        revised = copy.deepcopy(original)
        assert set(changes) <= {r['example_id'] for r in revised}
        for row in revised:
            if row['example_id'] in changes:
                for field in ('primary_intent', 'expected_route'):
                    row['gold'][field] = changes[row['example_id']][field]
        fields = ('intent_accuracy', 'intent_macro_f1', 'auto_count', 'unsafe_auto_count_routing_label', 'escalation_recall')
        results[system] = {name: {k: v for k, v in compute(rows).items() if k in fields}
                           for name, rows in (('original', original), ('supplemental', revised))}
    result = {'status': review['status'], 'note': 'Only intent and route sensitivity. Reply reference criteria and human ratings are unchanged. This is not a new model evaluation.', 'results': results}
    output = Path('artifacts/experiments/label_sensitivity.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
