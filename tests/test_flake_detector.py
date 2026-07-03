"""Pure flake-math tests — no database, just the classification logic."""

from __future__ import annotations

from quality_gate.flake.detector import Verdict, classify, failure_rate, is_consistent
from quality_gate.parser.models import Status

P, F, E, S = Status.PASSED, Status.FAILED, Status.ERROR, Status.SKIPPED


def test_all_pass_is_healthy():
    assert classify([P] * 10) is Verdict.HEALTHY


def test_all_fail_is_regression_not_flaky():
    assert classify([F] * 10) is Verdict.REGRESSION
    assert classify([E] * 10) is Verdict.REGRESSION  # errors count as failing too


def test_mixed_above_threshold_is_flaky():
    assert classify([F, F, P, P, P, P, P, P, P, P]) is Verdict.FLAKY  # 2/10 = 20%


def test_mixed_below_threshold_is_tolerated():
    assert classify([F, P, P, P, P, P, P, P, P, P]) is Verdict.HEALTHY  # 1/10 = 10%


def test_threshold_is_strictly_greater_than_15pct():
    assert classify([F, F, F] + [P] * 17) is Verdict.HEALTHY  # 3/20 = 15% -> not flaky
    assert classify([F, F, F, F] + [P] * 16) is Verdict.FLAKY  # 4/20 = 20% -> flaky


def test_insufficient_history_treats_failure_as_real():
    # 1 fail + 1 pass = 50%, but only 2 observations (< MIN_RUNS): do NOT quarantine,
    # so the current failure still blocks the gate (catch the bug).
    assert classify([F, P]) is Verdict.HEALTHY


def test_skips_excluded_and_flaky_with_enough_real_runs():
    window = [F, F, F, P, P, S, S, S, S, S]  # 3 fails + 2 pass = 5 counted, rate 60%
    assert failure_rate(window) == 0.6
    assert classify(window) is Verdict.FLAKY


def test_all_skipped_is_healthy():
    assert classify([S] * 10) is Verdict.HEALTHY


def test_is_consistent_gates_quarantine_exit():
    assert is_consistent([P] * 10)                            # recovered
    assert is_consistent([F] * 10)                            # regressed
    assert not is_consistent([F, P, P, P, P, P, P, P, P, P])  # still flapping
