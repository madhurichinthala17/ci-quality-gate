"""Normalized test-result model — the vocabulary the whole system speaks.

Everything downstream (flake engine, gate, triage, dashboards) depends on these
types, never on a specific file format. Each format adapter is responsible for
mapping its native representation onto this model, so adding a new format
(NUnit3, TRX, ...) never touches any stage but the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    """A test's outcome, normalized across formats.

    Every adapter maps its native representation onto exactly one of these.
    String-backed so it serializes cleanly into the JSON gate report.
    """

    PASSED = "passed"
    FAILED = "failed"    # an assertion failed — the product produced a wrong result
    ERROR = "error"      # the test crashed / could not complete (timeout, exception)
    SKIPPED = "skipped"  # did not run — excluded from flake and pass-rate math


# Outcomes that count as "this test failed" for gate + flake purposes.
# FAILED and ERROR stay distinct as Status values (triage categorizes them
# differently), but both are "failing" when deciding pass/fail and flakiness.
FAILING = (Status.FAILED, Status.ERROR)


@dataclass(frozen=True)
class TestResult:
    """One test's outcome in one run. Immutable value object."""

    __test__ = False  # domain model, not a pytest test case (name collides with Test* convention)

    id: str            # stable identity across runs: "classname::name" — flake-history key
    name: str
    classname: str
    suite: str
    status: Status
    duration: float                 # seconds
    message: str | None = None      # short summary, e.g. "assert 404 == 200"
    detail: str | None = None       # full text / stack trace (untrusted — bound before LLM)
    type: str | None = None         # exception / failure type, e.g. "AssertionError"

    @property
    def failing(self) -> bool:
        return self.status in FAILING


@dataclass
class TestRun:
    """All results from a single test run, plus convenience aggregates."""

    __test__ = False  # domain model, not a pytest test case (name collides with Test* convention)

    results: list[TestResult] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.results)

    @property
    def failing(self) -> list[TestResult]:
        return [r for r in self.results if r.failing]

    @property
    def passed(self) -> list[TestResult]:
        return [r for r in self.results if r.status is Status.PASSED]

    @property
    def skipped(self) -> list[TestResult]:
        return [r for r in self.results if r.status is Status.SKIPPED]

    def count(self, status: Status) -> int:
        return sum(1 for r in self.results if r.status is status)
