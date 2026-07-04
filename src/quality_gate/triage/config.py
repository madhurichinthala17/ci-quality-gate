"""Triage configuration — model choice and the safety limits, in one place."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TriageConfig:
    model: str = "claude-opus-4-8"  # default per Anthropic guidance; Haiku is a cost lever
    max_cost_usd: float = 0.50  # stop triaging once a run's spend reaches this
    detail_char_limit: int = 2000  # truncate untrusted failure text to this many chars
