"""Gate verdict model — the machine-readable result the CLI and CI consume.

`gate.Verdict` (PASS/WARN/FAIL) is the *release* decision, distinct from
`flake.Verdict` (HEALTHY/FLAKY/REGRESSION), which classifies a single test.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


_SEVERITY = {Verdict.PASS: 0, Verdict.WARN: 1, Verdict.FAIL: 2}


def worst(verdicts) -> Verdict:
    """The most severe verdict wins: FAIL > WARN > PASS. Empty -> PASS."""
    return max(verdicts, key=_SEVERITY.__getitem__, default=Verdict.PASS)


@dataclass
class CheckResult:
    name: str
    status: Verdict
    message: str
    metrics: dict = field(default_factory=dict)


@dataclass
class GateReport:
    verdict: Verdict
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        """True when the gate blocks the merge (used for the CLI exit code)."""
        return self.verdict is Verdict.FAIL

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "metrics": c.metrics,
                }
                for c in self.checks
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
