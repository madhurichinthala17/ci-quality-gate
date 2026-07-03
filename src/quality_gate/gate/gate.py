"""Gate orchestration — combine the checks into one verdict.

Pure composition: it gathers inputs (escape rate from the store), runs each check,
and takes the worst verdict. No decision logic lives here — that's in checks.py.
"""

from __future__ import annotations

from ..flake.engine import FlakeReport
from ..flake.store import HistoryStore
from ..parser.models import TestRun
from .checks import (
    check_coverage,
    check_defect_escape,
    check_failures,
    check_flake_rate,
    count_escapes,
)
from .config import GateConfig
from .coverage import Coverage
from .report import GateReport, worst


def compute_escape_rate(store: HistoryStore, window: int) -> float:
    """Fleet-wide PASS->FAIL transition rate over recent history."""
    escapes = transitions = 0
    for test_id in store.all_test_ids():
        oldest_first = list(reversed(store.window(test_id, window)))
        e, t = count_escapes(oldest_first)
        escapes += e
        transitions += t
    return escapes / transitions if transitions else 0.0


def run_gate(
    run: TestRun,
    flake: FlakeReport,
    coverage: Coverage | None = None,
    config: GateConfig | None = None,
    store: HistoryStore | None = None,
) -> GateReport:
    config = config or GateConfig()
    escape_rate = compute_escape_rate(store, config.escape_window) if store else 0.0
    checks = [
        check_failures(run, flake),
        check_flake_rate(run, flake, config),
        check_coverage(coverage, config),
        check_defect_escape(escape_rate, config),
    ]
    return GateReport(worst(c.status for c in checks), checks)
