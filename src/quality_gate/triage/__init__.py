"""LLM failure triage — classifies failures and drafts remediation tickets.

The LLM explains failures; it never decides the gate verdict (that's the
deterministic gate). Grounded, bounded, provider-swappable, cost-capped.
"""

from __future__ import annotations

from .config import TriageConfig
from .models import CostSummary, Ticket, TriageCategory, TriageReport
from .provider import FakeProvider, LLMProvider, LLMResponse, estimate_cost
from .triage import triage_tests

__all__ = [
    "TriageCategory",
    "Ticket",
    "CostSummary",
    "TriageReport",
    "TriageConfig",
    "LLMProvider",
    "LLMResponse",
    "FakeProvider",
    "estimate_cost",
    "triage_tests",
]
