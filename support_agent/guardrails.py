from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import DraftResult, EvidenceCase, IntentPrediction, Route
from .redact import redact_text

SENSITIVE_REQUEST = re.compile(r"\b(password|passcode|otp|one[- ]time password|cvv|pin)\b", re.I)
ACCOUNT_ACTION = re.compile(
    r"\b(refund(?:ed)?|cancel(?:led)?|unlock|charg(?:e|ed|eback)|change (?:my )?(?:address|email)|account|"
    r"marked (?:as )?delivered|delivered but|missing|stolen|guarantee|driver|damaged|broken|wrong item)\b",
    re.I,
)
COMPLETED_ACTION = re.compile(
    r"\b(?:we|i) (?:have |have now )?(?:refunded|cancelled|unlocked|credited|changed|issued)\b",
    re.I,
)
MONEY_OR_DEADLINE = re.compile(r"(?:[$£€₹]\s*\d|\b\d+\s*(?:hours?|days?|weeks?)\b)", re.I)
URL = re.compile(r"https?://\S+", re.I)


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reason_codes: tuple[str, ...]
    critical: bool = False
    repairable: bool = False


REASON_TEXT = {
    "SECURITY_RISK": "The message involves sensitive credentials and needs a secure human review.",
    "ACCOUNT_ACTION_REQUIRED": "This request needs an account-specific check or action that the agent cannot perform.",
    "AMBIGUOUS_INTENT": "The request is ambiguous and needs clarification from a human.",
    "LOW_INTENT_CONFIDENCE": "The predicted intent is not confident enough for automatic handling.",
    "INSUFFICIENT_EVIDENCE": "There is not enough relevant historical evidence to support an automatic reply.",
    "OUTPUT_VALIDATION_FAILED": "The draft did not pass the safety and grounding checks.",
    "MODEL_TIMEOUT": "The drafting service was unavailable, so the request was routed safely.",
    "TOOL_UNAVAILABLE": "Historical evidence could not be retrieved, so the request was routed safely.",
    "LOW_RISK_GROUNDED": "The request is low-risk and the reply is supported by relevant historical evidence.",
}


class GuardrailEngine:
    def __init__(self, *, intent_threshold: float | None, evidence_threshold: float | None) -> None:
        self.intent_threshold = intent_threshold
        self.evidence_threshold = evidence_threshold

    def precheck(self, message: str) -> CheckResult:
        codes = []
        if SENSITIVE_REQUEST.search(message):
            codes.append("SECURITY_RISK")
        if ACCOUNT_ACTION.search(message):
            codes.append("ACCOUNT_ACTION_REQUIRED")
        return CheckResult(not codes, tuple(codes), critical="SECURITY_RISK" in codes)

    def validate(self, draft: DraftResult, evidence: list[EvidenceCase]) -> CheckResult:
        codes = []
        retrieved_ids = {case.case_id for case in evidence}
        cited_ids = {case_id for claim in draft.claims for case_id in claim.source_case_ids}
        if not cited_ids or not cited_ids <= retrieved_ids:
            codes.append("OUTPUT_VALIDATION_FAILED")
        if SENSITIVE_REQUEST.search(draft.reply_text) or COMPLETED_ACTION.search(draft.reply_text):
            codes.append("OUTPUT_VALIDATION_FAILED")
        if redact_text(draft.reply_text) != draft.reply_text:
            codes.append("OUTPUT_VALIDATION_FAILED")
        sensitive_fragments = [*MONEY_OR_DEADLINE.findall(draft.reply_text), *URL.findall(draft.reply_text)]
        # Historical tweets are not current policy authority; exact deadlines, amounts,
        # and links require a separately approved knowledge source that this demo lacks.
        if sensitive_fragments:
            codes.append("OUTPUT_VALIDATION_FAILED")
        return CheckResult(not codes, tuple(dict.fromkeys(codes)), critical=bool(codes), repairable=False)

    def route(
        self,
        intent: IntentPrediction,
        evidence: list[EvidenceCase],
        draft: DraftResult,
    ) -> tuple[Route, tuple[str, ...]]:
        codes = []
        if draft.needs_human:
            codes.append("ACCOUNT_ACTION_REQUIRED")
        if evidence and evidence[0].evidence_type != "actionable_guidance":
            codes.append("INSUFFICIENT_EVIDENCE")
        if intent.ambiguous:
            codes.append("AMBIGUOUS_INTENT")
        if self.intent_threshold is None or intent.confidence is None or intent.confidence < self.intent_threshold:
            codes.append("LOW_INTENT_CONFIDENCE")
        best_score = max((case.score for case in evidence), default=0.0)
        if self.evidence_threshold is None or best_score < self.evidence_threshold:
            codes.append("INSUFFICIENT_EVIDENCE")
        if codes:
            return Route.ESCALATE, tuple(dict.fromkeys(codes))
        return Route.AUTO_HANDLE, ("LOW_RISK_GROUNDED",)


def primary_reason(codes: tuple[str, ...]) -> str:
    precedence = [
        "SECURITY_RISK",
        "ACCOUNT_ACTION_REQUIRED",
        "AMBIGUOUS_INTENT",
        "LOW_INTENT_CONFIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "TOOL_UNAVAILABLE",
        "MODEL_TIMEOUT",
        "OUTPUT_VALIDATION_FAILED",
        "LOW_RISK_GROUNDED",
    ]
    code = next((item for item in precedence if item in codes), codes[0] if codes else "INSUFFICIENT_EVIDENCE")
    return REASON_TEXT.get(code, "A human should review this request.")
