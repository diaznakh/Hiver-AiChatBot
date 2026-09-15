import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from evals.run_judge import call_judge, main


ENV = {'JUDGE_API_URL': 'https://example.invalid/chat/completions', 'JUDGE_API_KEY': 'test-secret', 'JUDGE_MODEL_ID': 'test-model'}
RATING = dict(groundedness=4, relevance=4, helpfulness=4, tone=4,
              privacy_violation=False, unsupported_action_claim=False,
              unsafe_instruction=False, critical_hallucination=False,
              justification='Test fixture only.', evidence_ids=[])


class JudgeTransportTests(unittest.TestCase):
    @patch.dict(os.environ, ENV)
    def test_error_details_redact_key_and_include_user_message(self):
        error = urllib.error.HTTPError(ENV['JUDGE_API_URL'], 400, 'Bad request', {}, io.BytesIO(b'Invalid request test-secret'))
        with patch('urllib.request.urlopen', side_effect=error) as request:
            with self.assertRaisesRegex(RuntimeError, r'Invalid request \[REDACTED\]'):
                call_judge('Rubric and case')
            payload = json.loads(request.call_args.args[0].data)
            self.assertIn('user', [m['role'] for m in payload['messages']])

    @patch.dict(os.environ, ENV)
    def test_resume_empty_file_then_skip_completed_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'judge.jsonl'
            output.touch()
            argv = ['judge', '--examples', 'data/golden_set.xlsx', '--predictions',
                    *[f'artifacts/official/predictions_{s}.jsonl' for s in ('b0','b1','b2')],
                    '--output', str(output), '--resume']
            with patch('sys.argv', argv), patch('evals.run_judge.call_judge', return_value=RATING) as judge, patch('builtins.print'):
                main()
                self.assertEqual(judge.call_count, 60)
                original = output.read_bytes()
                judge.reset_mock()
                main()
                judge.assert_not_called()
                self.assertEqual(output.read_bytes(), original)
                with patch.dict(os.environ, {'JUDGE_MODEL_ID': 'different-model'}):
                    with self.assertRaisesRegex(ValueError, 'differs'):
                        main()
                self.assertEqual(output.read_bytes(), original)

    @patch.dict(os.environ, ENV)
    def test_transient_error_retries(self):
        error = urllib.error.HTTPError(ENV['JUDGE_API_URL'], 429, 'Limit', {}, io.BytesIO(b'quota'))
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(RATING)}}]}).encode())
        with patch('urllib.request.urlopen', side_effect=[error, response]), patch('time.sleep') as sleep, patch('builtins.print'):
            self.assertEqual(call_judge('case'), RATING)
            sleep.assert_called_once_with(20)

    @patch.dict(os.environ, ENV)
    def test_timeout_then_success(self):
        response = io.BytesIO(json.dumps({'choices': [{'message': {'content': json.dumps(RATING)}}]}).encode())
        with patch('urllib.request.urlopen', side_effect=[TimeoutError(), response]) as request, patch('time.sleep') as sleep, patch('builtins.print'):
            self.assertEqual(call_judge('case'), RATING)
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(10)

    @patch.dict(os.environ, ENV)
    def test_timeouts_stop_after_four_attempts(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError()) as request, patch('time.sleep'), patch('builtins.print'):
            with self.assertRaisesRegex(RuntimeError, 'after 4 attempts'):
                call_judge('case')
            self.assertEqual(request.call_count, 4)

    @patch.dict(os.environ, ENV)
    def test_interrupted_run_resumes_without_losing_first_rating(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'judge.jsonl'
            argv = ['judge', '--examples', 'data/golden_set.xlsx', '--predictions',
                    *[f'artifacts/official/predictions_{s}.jsonl' for s in ('b0','b1','b2')],
                    '--output', str(output), '--resume']
            with patch('sys.argv', argv), patch('builtins.print'):
                with patch('evals.run_judge.call_judge', side_effect=[RATING, RuntimeError('timeout')]):
                    with self.assertRaisesRegex(RuntimeError, 'timeout'):
                        main()
                first = output.read_bytes()
                self.assertEqual(len(first.splitlines()), 1)
                with patch('evals.run_judge.call_judge', return_value=RATING) as judge:
                    main()
                    self.assertEqual(judge.call_count, 59)
                self.assertTrue(output.read_bytes().startswith(first))
                self.assertEqual(len(output.read_bytes().splitlines()), 60)
