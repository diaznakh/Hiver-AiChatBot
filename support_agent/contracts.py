from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Route(StrEnum):
    AUTO_HANDLE = "AUTO_HANDLE"
    ESCALATE = "ESCALATE"


class GroundingStatus(StrEnum):
    GROUNDED = "GROUNDED"
    TEMPLATE_ONLY = "TEMPLATE_ONLY"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class HistoryTurn:
    role: str
    text: str

    def __post_init__(self) -> None:
        if self.role not in {"customer", "brand"}:
            raise ValueError("history role must be customer or brand")
        if not self.text.strip():
            raise ValueError("history text cannot be empty")


@dataclass(frozen=True)
class AgentRequest:
    brand_id: str
    message: str
    history: tuple[HistoryTurn, ...] = ()
    channel: str = "offline_demo"

    def __post_init__(self) -> None:
        if not self.brand_id.strip():
            raise ValueError("brand_id is required")
        if not self.message.strip():
            raise ValueError("message is required")
        if len(self.message) > 2_000:
            raise ValueError("message exceeds 2,000 characters")
        if len(self.history) > 12:
            raise ValueError("history exceeds 12 turns")
        body_size = len(self.message.encode()) + sum(len(t.text.encode()) for t in self.history)
        if body_size > 16_384:
            raise ValueError("request exceeds 16 KB")


@dataclass(frozen=True)
class IntentPrediction:
    label: str
    confidence: float | None
    ambiguous: bool = False


@dataclass(frozen=True)
class EvidenceCase:
    case_id: str
    brand_id: str
    problem_excerpt: str
    response_excerpt: str
    source_tweet_ids: tuple[str, ...]
    source_timestamp: str
    evidence_type: str
    intent: str
    score: float = 0.0
    index_version: str = "unknown"
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    text: str
    source_case_ids: tuple[str, ...]


@dataclass(frozen=True)
class DraftResult:
    reply_text: str
    claims: tuple[Claim, ...] = ()
    needs_human: bool = False

    def __post_init__(self) -> None:
        if not self.reply_text.strip():
            raise ValueError("reply_text cannot be empty")
        if len(self.reply_text) > 600:
            raise ValueError("reply_text exceeds 600 characters")


@dataclass(frozen=True)
class AgentResult:
    intent: str
    intent_confidence: float | None
    draft: str
    route: Route
    reason_codes: tuple[str, ...]
    reason: str
    evidence: tuple[EvidenceCase, ...] = ()
    grounding_status: GroundingStatus = GroundingStatus.INSUFFICIENT
    degraded: bool = False
    delivery_status: str = "NOT_SENT"
    usage: dict[str, int | float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["route"] = self.route.value
        value["grounding_status"] = self.grounding_status.value
        return value

