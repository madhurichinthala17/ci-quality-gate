"""Flake engine tests — the quarantine state machine, driven build-by-build."""

from __future__ import annotations

from quality_gate.flake import SqliteHistoryStore, Verdict, evaluate
from quality_gate.parser.models import Status, TestResult, TestRun

P, F = Status.PASSED, Status.FAILED


def _run(test_id: str, status: Status) -> TestRun:
    classname, name = test_id.split("::")
    return TestRun(
        [TestResult(id=test_id, name=name, classname=classname, suite="s",
                    status=status, duration=0.0)]
    )


def _drive(store, test_id, statuses):
    """Feed one build per status; return the final FlakeReport."""
    report = None
    for s in statuses:
        report = evaluate(store, _run(test_id, s))
    return report


def test_healthy_test_is_never_quarantined(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    report = _drive(store, "t::a", [P] * 10)
    assert report.quarantined == set()


def test_flaky_test_enters_quarantine(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    # 8 pass then 2 fail -> 2/10 = 20% (>15%, >=MIN_RUNS) -> flaky on the last build
    report = _drive(store, "t::a", [P] * 8 + [F, F])
    assert "t::a" in report.quarantined
    assert "t::a" in report.newly_quarantined


def test_regression_blocks_and_is_not_quarantined(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    report = _drive(store, "t::a", [F] * 6)  # consistent failure
    assert "t::a" in report.regressions
    assert "t::a" not in report.quarantined  # a real bug must block, never be forgiven


def test_thin_evidence_does_not_quarantine(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    report = _drive(store, "t::a", [P, F])  # 50% but only 2 runs (< MIN_RUNS)
    assert "t::a" not in report.quarantined
    assert report.verdicts["t::a"] is Verdict.HEALTHY  # treated as real -> gate blocks


def test_quarantined_stays_until_consistent_then_releases(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    _drive(store, "t::a", [P] * 8 + [F, F])          # quarantined at 20%
    # 9 more passes: the window's failure rate dips to ~10% but a fail remains,
    # so it stays quarantined — this is the anti-flapping property.
    still = _drive(store, "t::a", [P] * 9)
    assert "t::a" in still.quarantined
    # the 10th consecutive pass makes the window all-pass -> recovered -> released
    released = _drive(store, "t::a", [P])
    assert "t::a" not in released.quarantined
    assert "t::a" in released.released
