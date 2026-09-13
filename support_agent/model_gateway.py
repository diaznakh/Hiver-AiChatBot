from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .contracts import Claim, DraftResult, EvidenceCase, IntentPrediction
from .grounding import supported_guidance, UnsupportedEvidenceError


@dataclass
class UsageBudget:
    max_input_tokens: int = 8_000
    max_output_tokens: int = 900
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 0

    @staticmethod
    def estimate(text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    def reserve(self, input_text: str, max_output: int = 300) -> None:
        incoming = self.estimate(input_text)
        if self.input_tokens + incoming > self.max_input_tokens:
            raise BudgetError("input token budget exceeded")
        if self.output_tokens + max_output > self.max_output_tokens:
            raise BudgetError("output token budget exceeded")
        self.input_tokens += incoming
        self.output_tokens += max_output
        self.attempts += 1


class BudgetError(RuntimeError):
    pass


class DeterministicDraftGateway:
    """Offline action selector conditioned on customer topic and historical response."""

    def draft(
        self,
        message: str,
        intent: IntentPrediction,
        evidence: list[EvidenceCase],
        budget: UsageBudget,
    ) -> DraftResult:
        if not evidence:
            raise ValueError("evidence is required")
        packed = f"intent={intent.label}\nmessage={message}\nevidence={evidence}"
        budget.reserve(packed)
        claims = []
        for case in evidence:
            if case.evidence_type != "actionable_guidance":
                continue
            for guidance in supported_guidance(message, case.response_excerpt):
                if guidance not in {claim.text for claim in claims}:
                    claims.append(Claim(guidance, (case.case_id,)))
        if not claims:
            raise UnsupportedEvidenceError("No supported low-risk guidance in retrieved responses")
        claims = claims[:2]
        response = "I’m sorry you’re dealing with this. " + " ".join(c.text for c in claims)
        needs_human = intent.label in {
            "return_refund", "order_change", "payment_charge", "account_prime", "product_issue", "other_unclear"
        }
        return DraftResult(response, tuple(claims), needs_human=needs_human)


class ChatCompletionsDraftGateway:
    """Provider-neutral adapter for a configured OpenAI-compatible chat-completions endpoint."""

    def __init__(self, *, url: str, api_key: str, model: str, prompt_path: str | Path) -> None:
        if not all((url, api_key, model)):
            raise ValueError("live gateway requires URL, API key, and model ID")
        self.url = url
        self.api_key = api_key
        self.model = model
        self.system_prompt = Path(prompt_path).read_text()

    def draft(
        self,
        message: str,
        intent: IntentPrediction,
        evidence: list[EvidenceCase],
        budget: UsageBudget,
    ) -> DraftResult:
        case_payload = [
            {
                "case_id": case.case_id,
                "problem": case.problem_excerpt,
                "historical_response": case.response_excerpt,
                "evidence_type": case.evidence_type,
            }
            for case in evidence
        ]
        user_payload = json.dumps(
            {"intent": intent.label, "customer_message": message, "evidence": case_payload},
            ensure_ascii=False,
        )
        budget.reserve(self.system_prompt + user_payload)
        request_body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_payload},
                ],
            }
        ).encode()
        request = urllib.request.Request(
            self.url,
            data=request_body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5.0) as response:
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        allowed_ids = {case.case_id for case in evidence}
        claims = []
        for row in parsed.get("claims", []):
            source_ids = tuple(row.get("source_case_ids", []))
            if not set(source_ids) <= allowed_ids:
                raise ValueError("model cited an unretrieved evidence case")
            claims.append(Claim(str(row["text"]), source_ids))
        return DraftResult(
            reply_text=str(parsed["reply_text"]),
            claims=tuple(claims),
            needs_human=bool(parsed.get("needs_human", False)),
        )
