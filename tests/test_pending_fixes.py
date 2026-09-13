import tempfile
import unittest
import json
import subprocess
import sys
from pathlib import Path
from support_agent.contracts import EvidenceCase, IntentPrediction
from support_agent.model_gateway import DeterministicDraftGateway, UsageBudget
from support_agent.grounding import UnsupportedEvidenceError
from evals.judge import build_prompt, validate_rating
from evals.ratings import load, passed
from evals.metrics import macro_f1


class PendingFixTests(unittest.TestCase):
    def case(self, text):
        return EvidenceCase('one', 'AmazonHelp', 'video app issue', text, ('1','2'), '2017', 'actionable_guidance', 'digital_service')

    def test_reply_changes_with_evidence(self):
        gateway = DeterministicDraftGateway()
        intent = IntentPrediction('digital_service', .9)
        restart = gateway.draft('My video app is broken', intent, [self.case('Please restart the app.')], UsageBudget())
        update = gateway.draft('My video app is broken', intent, [self.case('Please install the latest update.')], UsageBudget())
        self.assertNotEqual(restart.reply_text, update.reply_text)
        self.assertIn('restart', restart.reply_text)
        self.assertNotIn('restart', update.reply_text)
        self.assertEqual(restart.claims[0].source_case_ids, ('one',))

    def test_unrelated_or_missing_guidance_rejected(self):
        for message, response in [('Video app fails', 'We are sorry.'), ('My parcel is late', 'Restart the app.')]:
            with self.assertRaises(UnsupportedEvidenceError):
                DeterministicDraftGateway().draft(message, IntentPrediction('digital_service', .9), [self.case(response)], UsageBudget())

    def test_shared_rubric_in_judge(self):
        prompt = build_prompt({'message':'x', 'labels':{}}, {'draft':'y'}, [])
        self.assertIn('Shared human and LLM', prompt)
        self.assertIn('| 1 |', prompt)
        self.assertIn('| 5 |', prompt)

    def test_boolean_is_not_ordinal_score(self):
        with self.assertRaises(ValueError):
            validate_rating({'groundedness': True}, set())

    def test_empty_ratings_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'empty.jsonl'
            path.touch()
            with self.assertRaises(ValueError):
                load(path)

    def test_fixed_macro_denominator(self):
        value, details = macro_f1(['delivery_tracking'], ['delivery_tracking'])
        self.assertEqual(len(details), 8)
        self.assertEqual(value, 1/8)

    def test_safety_flag_overrides_high_scores(self):
        rating = dict.fromkeys(('groundedness','relevance','helpfulness','tone'), 5)
        rating.update(dict.fromkeys(('privacy_violation','unsupported_action_claim','unsafe_instruction','critical_hallucination'), False))
        self.assertTrue(passed(rating))
        rating['unsafe_instruction'] = True
        self.assertFalse(passed(rating))

    def test_negated_guidance_rejected(self):
        with self.assertRaises(UnsupportedEvidenceError):
            DeterministicDraftGateway().draft('My video app fails', IntentPrediction('digital_service', .9), [self.case('Do not restart the app.')], UsageBudget())

    def test_agreement_pipeline_with_controlled_fixtures(self):
        from evals.blinding import blinded_output_id
        from evals.ratings import DIMENSIONS, FLAGS
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            predictions = root / 'predictions.jsonl'
            ratings = root / 'ratings.jsonl'
            output = root / 'agreement.json'
            predictions.write_text('\n'.join(json.dumps({'output_id': f'fixture_{i}::b2', 'system_id':'b2'}) for i in range(2)))
            rows = []
            for i in range(2):
                rating = dict.fromkeys(DIMENSIONS, 3+i)
                rating.update(dict.fromkeys(FLAGS, False))
                rows.append({'output_id': blinded_output_id(f'fixture_{i}::b2', 20260912), 'rating': rating})
            ratings.write_text('\n'.join(map(json.dumps, rows)))
            subprocess.run([sys.executable, '-m', 'evals.score_agreement', '--human', str(ratings), '--judge', str(ratings), '--predictions', str(predictions), '--output', str(output)], check=True, capture_output=True)
            result = json.loads(output.read_text())
            self.assertEqual(result['ordinal_weighted_kappa']['tone'], 1)
            self.assertEqual(result['by_system']['b2']['human']['quality_pass_rate'], .5)
