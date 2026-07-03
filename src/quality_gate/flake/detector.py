"""Flake detection math — pure functions over one test's recent outcome window.

No I/O here on purpose: given the last N outcomes for a single test, decide
whether it is healthy, a real regression, or flaky. Keeping the interview-
critical logic pure makes it trivially unit-testable without a database.

Design bias: a failure is REAL until proven flaky. Real failures are caught on
the first build they occur; the window only governs when we *forgive* a test
that has a proven track record of intermittency. We never quarantine on thin
evidence (see MIN_RUNS), so a genuine bug is never hidden by mistake.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

from ..parser.models import FAILING, Status

WINDOW = 10             # rolling window: the last 10 builds
FLAKE_THRESHOLD = 0.15  # a mixed test failing >15% of the time is "flaky"
MIN_RUNS = 5            # need >=5 pass/fail observations before trusting a "flaky" call


class Verdict(str, Enum):
    HEALTHY = "healthy"        # not flaky -> the gate treats any current failure as real
    FLAKY = "flaky"            # inconsistent, above threshold, with enough evidence
    REGRESSION = "regression"  # consistent failure — fails every time it runs (a real bug)


def _counts(window: Sequence[Status]) -> tuple[int, int]:
    """(passes, fails) over the window. Skips are ignored — they are neither."""
    fails = sum(1 for s in window if s in FAILING)
    passes = sum(1 for s in window if s is Status.PASSED)
    return passes, fails


def failure_rate(window: Sequence[Status]) -> float:
    passes, fails = _counts(window)
    total = passes + fails
    return fails / total if total else 0.0


def classify(
    window: Sequence[Status],
    threshold: float = FLAKE_THRESHOLD,
    min_runs: int = MIN_RUNS,
) -> Verdict:
    passes, fails = _counts(window)
    total = passes + fails
    if total == 0 or fails == 0:
        return Verdict.HEALTHY
    if passes == 0:
        return Verdict.REGRESSION            # 100% fail — consistent, so it's a real bug
    # Mixed record. Only forgive it as flaky with enough evidence AND above the
    # noise threshold; otherwise treat the failure as real so the gate blocks.
    if total >= min_runs and fails / total > threshold:
        return Verdict.FLAKY
    return Verdict.HEALTHY


def is_consistent(window: Sequence[Status]) -> bool:
    """True when the test is no longer intermittent — all pass or all fail.

    This is the quarantine EXIT rule: a quarantined test is released only once it
    stops flapping (recovered to all-pass, or degraded to a real regression),
    never merely because its rate dipped below the entry threshold.
    """
    passes, fails = _counts(window)
    return fails == 0 or passes == 0
