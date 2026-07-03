"""Flake detection: statistical classification of tests over a rolling build window."""

from __future__ import annotations

from .detector import (
    FLAKE_THRESHOLD,
    MIN_RUNS,
    WINDOW,
    Verdict,
    classify,
    failure_rate,
    is_consistent,
)

__all__ = [
    "Verdict",
    "classify",
    "failure_rate",
    "is_consistent",
    "WINDOW",
    "FLAKE_THRESHOLD",
    "MIN_RUNS",
]
