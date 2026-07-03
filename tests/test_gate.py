"""Gate orchestration — integration tests wiring flake + coverage + checks."""

from __future__ import annotations

from quality_gate.flake import SqliteHistoryStore, evaluate
from quality_gate.gate import Coverage, Verdict, run_gate
from quality_gate.parser.models import Status, TestResult, TestRun

P, F = Status.PASSED, Status.FAILED
GOOD_COV = Coverage(0.90, 0.85)


def _run(*specs: tuple[str, Status]) -> TestRun:
    return TestRun(
        [TestResult(id=i, name=i, classname="t", suite="s", status=s, duration=0.0)
         for i, s in specs]
    )


def test_all_green_passes(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    run = _run(("t::a", P), ("t::b", P))
    flake = evaluate(store, run)
    report = run_gate(run, flake, coverage=GOOD_COV, store=store)
    assert report.verdict is Verdict.PASS


def test_real_failure_fails(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    run = _run(("t::a", F), ("t::b", P))
    flake = evaluate(store, run)
    report = run_gate(run, flake, coverage=GOOD_COV, store=store)
    assert report.verdict is Verdict.FAIL


def test_low_coverage_fails(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    run = _run(("t::a", P))
    flake = evaluate(store, run)
    report = run_gate(run, flake, coverage=Coverage(0.50, 0.50), store=store)
    assert report.verdict is Verdict.FAIL


def test_quarantined_flaky_failure_does_not_block(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    flaky = "t::flaky"
    # Build history so the flaky test crosses the threshold: 8 pass, then a fail.
    for s in [P] * 8 + [F]:
        evaluate(store, _run((flaky, s)))
    # Final build: the flaky test fails again (now 2/10 = 20% -> quarantined), alongside
    # 4 healthy tests so the fleet flake rate stays within the 20% limit.
    run = _run((flaky, F), ("t::a", P), ("t::b", P), ("t::c", P), ("t::d", P))
    flake = evaluate(store, run)
    assert flaky in flake.quarantined
    report = run_gate(run, flake, coverage=GOOD_COV, store=store)
    assert report.verdict is not Verdict.FAIL  # the only failure is a quarantined flake
