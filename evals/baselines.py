from __future__ import annotations

from support_agent.contracts import AgentRequest, Route
from support_agent.guardrails import ACCOUNT_ACTION_HARD, ACCOUNT_ACTION_SOFT, SENSITIVE_REQUEST


def run_b0(example: dict) -> dict:
    """Constant-intent baseline; intentionally not a fitted majority predictor."""
    return {
        "intent": "delivery_tracking",
        "route": Route.ESCALATE.value,
        "draft": "Thanks for contacting us. A support specialist will review your request.",
        "evidence_ids": [],
        "reason_codes": ["TRIVIAL_ALWAYS_ESCALATE"],
        "degraded": False,
    }


def run_b1(example: dict, classifier, repository) -> dict:
    message = example["message"]
    intent = classifier.predict(message)
    evidence = repository.search(message, intent.label, 1)
    risky = bool(ACCOUNT_ACTION_HARD.search(message) or ACCOUNT_ACTION_SOFT.search(message) or SENSITIVE_REQUEST.search(message))
    route = Route.ESCALATE if risky or intent.ambiguous or not evidence else Route.AUTO_HANDLE
    draft = evidence[0].response_excerpt if evidence else "A support specialist will review your request."
    return {
        "intent": intent.label,
        "intent_confidence": intent.confidence,
        "route": route.value,
        "draft": draft,
        "evidence_ids": [case.case_id for case in evidence],
        "reason_codes": ["SIMPLE_RISK_RULE"] if risky else ["SIMPLE_RETRIEVAL_RULE"],
        "degraded": False,
    }


def run_b2(example: dict, agent) -> dict:
    result = agent.run(AgentRequest(brand_id="AmazonHelp", message=example["message"]))
    payload = result.to_dict()
    payload["evidence_ids"] = [case["case_id"] for case in payload.pop("evidence")]
    return payload
