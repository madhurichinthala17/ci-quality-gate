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
from .engine import FlakeReport, evaluate
from .store import HistoryStore, SqliteHistoryStore

__all__ = [
    "Verdict",
    "classify",
    "failure_rate",
    "is_consistent",
    "WINDOW",
    "FLAKE_THRESHOLD",
    "MIN_RUNS",
    "evaluate",
    "FlakeReport",
    "HistoryStore",
    "SqliteHistoryStore",
]
