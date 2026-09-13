import unittest

from support_agent.contracts import AgentRequest, Route
from support_agent.factory import build_agent


class AgentTests(unittest.TestCase):
    def test_low_risk_grounded_delivery_can_be_recommended(self) -> None:
        result = build_agent(".").run(AgentRequest("AmazonHelp", "My parcel is late and tracking has not moved"))
        self.assertEqual(result.intent, "delivery_tracking")
        self.assertIn(result.route, (Route.AUTO_HANDLE, Route.ESCALATE))
        self.assertEqual(result.delivery_status, "NOT_SENT")
        self.assertTrue(result.evidence)

    def test_account_action_escalates_without_completed_claim(self) -> None:
        result = build_agent(".").run(AgentRequest("AmazonHelp", "My return was collected; refund me now"))
        self.assertEqual(result.route, Route.ESCALATE)
        self.assertIn("ACCOUNT_ACTION_REQUIRED", result.reason_codes)
        self.assertNotIn("refunded", result.draft.lower())
        self.assertTrue(result.evidence)

    def test_credential_request_escalates(self) -> None:
        result = build_agent(".").run(AgentRequest("AmazonHelp", "My OTP is 123456 and I cannot login"))
        self.assertEqual(result.route, Route.ESCALATE)
        self.assertIn("SECURITY_RISK", result.reason_codes)
        self.assertNotIn("123456", result.draft)

    def test_brand_scope_cannot_be_overridden(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported brand"):
            build_agent(".").run(AgentRequest("AnotherBrand", "My parcel is late"))


if __name__ == "__main__":
    unittest.main()
