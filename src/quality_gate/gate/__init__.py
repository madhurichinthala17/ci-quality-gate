"""Deterministic quality gate — combines checks into one PASS/WARN/FAIL verdict."""

from __future__ import annotations

from .config import GateConfig
from .coverage import Coverage, parse_coverage
from .gate import compute_escape_rate, run_gate
from .report import CheckResult, GateReport, Verdict, worst

__all__ = [
    "Verdict",
    "CheckResult",
    "GateReport",
    "worst",
    "Coverage",
    "parse_coverage",
    "GateConfig",
    "run_gate",
    "compute_escape_rate",
]
