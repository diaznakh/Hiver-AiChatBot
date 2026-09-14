from __future__ import annotations

from .contracts import AgentRequest, AgentResult, GroundingStatus, Route
from .guardrails import GuardrailEngine, primary_reason
from .model_gateway import BudgetError, DeterministicDraftGateway, UsageBudget
from .redact import redact_text
from .grounding import UnsupportedEvidenceError


class SupportOrchestrator:
    def __init__(self, classifier, repository, guardrails: GuardrailEngine, model=None) -> None:
        self.classifier = classifier
        self.repository = repository
        self.guardrails = guardrails
        self.model = model or DeterministicDraftGateway()

    def handoff(self, intent, codes, *, degraded=False, evidence=()) -> AgentResult:
        draft = "I’m sorry you’re dealing with this. Human support needs to review your request. I cannot check account details or perform account actions."
        return AgentResult(
            intent=intent.label,
            intent_confidence=intent.confidence,
            draft=draft,
            route=Route.ESCALATE,
            reason_codes=tuple(codes),
            reason=primary_reason(tuple(codes)),
            evidence=tuple(evidence),
            grounding_status=GroundingStatus.TEMPLATE_ONLY,
            degraded=degraded,
        )

    def run(self, request: AgentRequest) -> AgentResult:
        if request.brand_id != self.repository.brand_id:
            raise ValueError("unsupported brand")
        clean_message = redact_text(request.message)
        clean_history = tuple(type(turn)(turn.role, redact_text(turn.text)) for turn in request.history)
        intent = self.classifier.predict(clean_message, clean_history)
        precheck = self.guardrails.precheck(clean_message)

        try:
            evidence = self.repository.search(clean_message, intent.label, 5)
        except Exception:
            return self.handoff(intent, ("TOOL_UNAVAILABLE",), degraded=True)
        if not evidence:
            return self.handoff(intent, ("INSUFFICIENT_EVIDENCE",))

        budget = UsageBudget()
        try:
            draft = self.model.draft(clean_message, intent, evidence, budget)
        except UnsupportedEvidenceError:
            codes = precheck.reason_codes or ("INSUFFICIENT_EVIDENCE",)
            return self.handoff(intent, codes, evidence=evidence)
        except BudgetError:
            return self.handoff(intent, ("BUDGET_EXCEEDED",), degraded=True, evidence=evidence)
        except Exception:
            return self.handoff(intent, ("MODEL_TIMEOUT",), degraded=True, evidence=evidence)

        validation = self.guardrails.validate(draft, evidence)
        if not validation.passed:
            return self.handoff(intent, validation.reason_codes, evidence=evidence)
        if not precheck.passed:
            return AgentResult(
                intent=intent.label,
                intent_confidence=intent.confidence,
                draft=draft.reply_text,
                route=Route.ESCALATE,
                reason_codes=precheck.reason_codes,
                reason=primary_reason(precheck.reason_codes),
                evidence=tuple(evidence),
                grounding_status=GroundingStatus.GROUNDED,
                usage={
                    "estimated_input_tokens": budget.input_tokens,
                    "reserved_output_tokens": budget.output_tokens,
                    "model_attempts": budget.attempts,
                },
            )
        route, reason_codes = self.guardrails.route(intent, evidence, draft)
        return AgentResult(
            intent=intent.label,
            intent_confidence=intent.confidence,
            draft=draft.reply_text,
            route=route,
            reason_codes=reason_codes,
            reason=primary_reason(reason_codes),
            evidence=tuple(evidence),
            grounding_status=GroundingStatus.GROUNDED,
            usage={
                "estimated_input_tokens": budget.input_tokens,
                "reserved_output_tokens": budget.output_tokens,
                "model_attempts": budget.attempts,
            },
        )
