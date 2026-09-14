import copy
import unittest

from evals.calibrate import select_candidate, validate_reviewed
from evals.run import validate_evaluation, validate_reviewed_examples
from support_agent.grounding import supported_guidance


class DevelopmentTests(unittest.TestCase):
    def row(self):
        return {
            "example_id": "dev001", "conversation_id": "c001", "split": "dev",
            "message": "My video app fails",
            "labels": {"primary_intent": "digital_service", "expected_route": "ESCALATE",
                       "acceptable_points": ["Human support needs to review this."], "forbidden_claims": []},
            "annotation": {"annotator_id": "fixture reviewer", "reviewed": True},
            "metadata": {"synthetic": False, "weak_labels": False},
        }

    def test_zero_coverage_is_not_calibration_success(self):
        self.assertIsNone(select_candidate([(0.0, 1.0, 0.0, .95, 8.0, 0, 0)]))
        self.assertIsNone(select_candidate([]))

    def test_useful_candidate_selected(self):
        candidate = (.2, 1.0, 0.0, .8, 1.0, 10, 0)
        self.assertEqual(select_candidate([candidate, (0.0, 1.0, 0.0, .95, 8.0, 0, 0)]), candidate)

    def test_calibration_rejects_test_split(self):
        row = self.row()
        row["split"] = "test"
        with self.assertRaisesRegex(ValueError, "development"):
            validate_reviewed([row])

    def test_review_mark_requires_complete_labels_and_name(self):
        for section, key in (("annotation", "annotator_id"), ("labels", "primary_intent")):
            row = self.row()
            row[section][key] = None
            with self.assertRaises(ValueError):
                validate_reviewed_examples([row])

    def test_duplicate_ids_rejected(self):
        for field in ("example_id", "conversation_id"):
            row = self.row()
            second = copy.deepcopy(row)
            second.update(example_id="dev002", conversation_id="c002")
            second[field] = row[field]
            with self.assertRaisesRegex(ValueError, field):
                validate_reviewed_examples([row, second])

    def test_development_cannot_be_official(self):
        validate_evaluation([self.row()], "development", "dev")
        with self.assertRaisesRegex(ValueError, "test split"):
            validate_evaluation([self.row()], "official", "dev")

    def test_keep_us_updated_is_not_software_guidance(self):
        self.assertEqual(supported_guidance("My video app fails", "Please install it. Keep us updated!"), [])
        self.assertTrue(supported_guidance("My video app fails", "Please install the latest update."))

    def test_feature_question_does_not_trigger_restart(self):
        self.assertEqual(supported_guidance("Can Alexa use another accent?", "Please restart the device."), [])
        self.assertTrue(supported_guidance("My video app is stuttering", "Please restart the device."))
