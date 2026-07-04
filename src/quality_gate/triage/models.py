"""Triage domain model — the vocabulary of the LLM failure-triage stage.

Depends on nothing but stdlib. The LLM's job is to classify a failure into the
closed `TriageCategory` set and draft a remediation ticket; it never decides the
gate verdict. `UNKNOWN` + `grounded=False` is the honest escape hatch for when
the failure text doesn't contain enough to classify — the model must not invent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TriageCategory(StrEnum):
    ASSERTION = "assertion"  # the product produced a wrong result (an assertion failed)
    TIMEOUT = "timeout"  # the test timed out or ran too slow
    ENVIRONMENT = "environment"  # infrastructure / config / setup problem
    DEPENDENCY = "dependency"  # an external service or dependency failed
    UNKNOWN = "unknown"  # not enough information to classify (ungrounded)


@dataclass(frozen=True)
class Ticket:
    """A remediation ticket for one failing/quarantined test."""

    test_id: str
    category: TriageCategory
    probable_cause: str
    suggested_next_step: str
    grounded: bool = True  # False when the model lacked enough info to be confident

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "category": self.category.value,
            "probable_cause": self.probable_cause,
            "suggested_next_step": self.suggested_next_step,
            "grounded": self.grounded,
        }


@dataclass
class CostSummary:
    """Running token/cost totals for a triage run — the observability record."""

    provider: str = ""
    model: str = ""
    calls: int = 0
    deduped: int = 0  # failures skipped because an identical one was already triaged
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0

    def add(self, input_tokens: int, output_tokens: int, usd: float) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.usd += usd

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": self.calls,
            "deduped": self.deduped,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "usd": round(self.usd, 6),
        }


@dataclass
class TriageReport:
    """Result of triaging a set of tests: tickets plus the production-behavior record."""

    tickets: list[Ticket] = field(default_factory=list)
    cost: CostSummary = field(default_factory=CostSummary)
    skipped: list[str] = field(default_factory=list)  # test_ids not triaged (cost cap hit)
    degraded: bool = False
    degraded_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "tickets": [t.to_dict() for t in self.tickets],
            "cost": self.cost.to_dict(),
            "skipped": self.skipped,
            "degraded": self.degraded,
            "degraded_reason": self.degraded_reason,
        }
