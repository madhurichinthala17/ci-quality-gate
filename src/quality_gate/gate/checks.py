"""The gate's decision logic — pure functions, one per check.

No I/O here: each check receives already-loaded data and returns a CheckResult.
The orchestrator (gate.py) supplies the inputs and combines the results.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..flake.engine import FlakeReport
from ..parser.models import FAILING, Status, TestRun
from .config import GateConfig
from .coverage import Coverage
from .report import CheckResult, Verdict


def check_coverage(coverage: Coverage | None, config: GateConfig) -> CheckResult:
    if coverage is None:
        return CheckResult("coverage", Verdict.WARN, "coverage not measured")
    pct = coverage.line_pct
    metrics = {"line_pct": round(pct, 2), "threshold": config.min_coverage}
    if pct < config.min_coverage:
        return CheckResult(
            "coverage", Verdict.FAIL,
            f"line coverage {pct:.1f}% is below the {config.min_coverage:.1f}% threshold",
            metrics,
        )
    return CheckResult(
        "coverage", Verdict.PASS,
        f"line coverage {pct:.1f}% meets the {config.min_coverage:.1f}% threshold",
        metrics,
    )


def check_failures(run: TestRun, flake: FlakeReport) -> CheckResult:
    failing = run.failing
    blocking = [r for r in failing if r.id not in flake.quarantined]
    suppressed = [r for r in failing if r.id in flake.quarantined]
    if blocking:
        return CheckResult(
            "failures", Verdict.FAIL,
            f"{len(blocking)} real failure(s) block the gate: {sorted(r.id for r in blocking)}",
            {"blocking": sorted(r.id for r in blocking)},
        )
    if suppressed:
        return CheckResult(
            "failures", Verdict.WARN,
            f"{len(suppressed)} failing test(s) suppressed by quarantine",
            {"suppressed": sorted(r.id for r in suppressed)},
        )
    return CheckResult("failures", Verdict.PASS, "no blocking failures")


def check_flake_rate(run: TestRun, flake: FlakeReport, config: GateConfig) -> CheckResult:
    run_ids = {r.id for r in run.results}
    quarantined = len(flake.quarantined & run_ids)
    rate = quarantined / len(run_ids) if run_ids else 0.0
    metrics = {"flake_rate": round(rate, 3), "limit": config.max_flake_rate}
    if rate > config.max_flake_rate:
        return CheckResult(
            "flake_rate", Verdict.FAIL,
            f"flake rate {rate:.0%} exceeds the {config.max_flake_rate:.0%} limit",
            metrics,
        )
    return CheckResult(
        "flake_rate", Verdict.PASS,
        f"flake rate {rate:.0%} within the {config.max_flake_rate:.0%} limit",
        metrics,
    )


def count_escapes(oldest_first: Sequence[Status]) -> tuple[int, int]:
    """(escapes, transitions) — a PASS->FAIL step is a defect escaping into a build."""
    escapes = transitions = 0
    for prev, cur in zip(oldest_first, oldest_first[1:]):
        transitions += 1
        if prev is Status.PASSED and cur in FAILING:
            escapes += 1
    return escapes, transitions


def check_defect_escape(escape_rate: float, config: GateConfig) -> CheckResult:
    metrics = {"escape_rate": round(escape_rate, 3), "limit": config.max_escape_rate}
    if escape_rate > config.max_escape_rate:
        return CheckResult(
            "defect_escape", Verdict.WARN,
            f"defect escape rate {escape_rate:.0%} exceeds the {config.max_escape_rate:.0%} limit",
            metrics,
        )
    return CheckResult(
        "defect_escape", Verdict.PASS,
        f"defect escape rate {escape_rate:.0%} within the {config.max_escape_rate:.0%} limit",
        metrics,
    )
