"""Pure gate-check tests — no I/O, just decision logic."""

from __future__ import annotations

from quality_gate.flake.engine import FlakeReport
from quality_gate.gate.checks import (
    check_coverage,
    check_defect_escape,
    check_failures,
    check_flake_rate,
    count_escapes,
)
from quality_gate.gate.config import GateConfig
from quality_gate.gate.coverage import Coverage
from quality_gate.gate.report import Verdict
from quality_gate.parser.models import Status, TestResult, TestRun

CFG = GateConfig()
P, F = Status.PASSED, Status.FAILED


def _run(*specs: tuple[str, Status]) -> TestRun:
    return TestRun(
        [
            TestResult(id=i, name=i, classname="t", suite="s", status=s, duration=0.0)
            for i, s in specs
        ]
    )


def test_coverage_pass_fail_and_warn_when_missing():
    assert check_coverage(Coverage(0.90, 0.0), CFG).status is Verdict.PASS
    assert check_coverage(Coverage(0.50, 0.0), CFG).status is Verdict.FAIL
    assert check_coverage(None, CFG).status is Verdict.WARN


def test_failures_block_unless_quarantined():
    run = _run(("t::a", F))
    assert check_failures(run, FlakeReport()).status is Verdict.FAIL  # real failure blocks
    assert (
        check_failures(run, FlakeReport(quarantined={"t::a"})).status is Verdict.WARN
    )  # suppressed
    assert check_failures(_run(("t::a", P)), FlakeReport()).status is Verdict.PASS


def test_flake_rate_limit_is_20_percent():
    run = _run(("t::a", P), ("t::b", P), ("t::c", P), ("t::d", P), ("t::e", P))
    assert (
        check_flake_rate(run, FlakeReport(quarantined={"t::a"}), CFG).status is Verdict.PASS
    )  # 20% == limit
    assert (
        check_flake_rate(run, FlakeReport(quarantined={"t::a", "t::b"}), CFG).status is Verdict.FAIL
    )  # 40%


def test_count_escapes_counts_pass_to_fail_transitions():
    assert count_escapes([P, F, P, F]) == (2, 3)
    assert count_escapes([P, P, P]) == (0, 2)
    assert count_escapes([F, P]) == (0, 1)


def test_defect_escape_warns_over_limit():
    assert check_defect_escape(0.05, CFG).status is Verdict.PASS
    assert check_defect_escape(0.20, CFG).status is Verdict.WARN
