import json
import tempfile
import unittest
from pathlib import Path
from evals.check_submission import require_complete_ratings
from evals.ratings import DIMENSIONS, FLAGS


class SubmissionTests(unittest.TestCase):
    def test_partial_ratings_do_not_count_as_complete(self):
        rating = {**dict.fromkeys(DIMENSIONS, 4), **dict.fromkeys(FLAGS, False)}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ratings.jsonl'
            path.write_text(json.dumps({'output_id': 'one', 'rating': rating}) + '\n')
            with self.assertRaisesRegex(ValueError, 'exactly'):
                require_complete_ratings(path, {'one', 'two'})
            self.assertEqual(set(require_complete_ratings(path, {'one'})), {'one'})
