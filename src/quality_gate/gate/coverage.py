"""Coverage report adapter — reads Cobertura `coverage.xml` (pytest-cov's format).

A separate adapter from the JUnit one: coverage is a different schema, so it gets
its own reader. The root element is <coverage line-rate=".." branch-rate="..">,
where the rates are fractions in 0..1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import parse as et_parse


@dataclass(frozen=True)
class Coverage:
    line_rate: float    # 0..1
    branch_rate: float  # 0..1

    @property
    def line_pct(self) -> float:
        return self.line_rate * 100.0

    @property
    def branch_pct(self) -> float:
        return self.branch_rate * 100.0


def parse_coverage(path: str | Path) -> Coverage:
    root = et_parse(path).getroot()
    if root.tag != "coverage":
        raise ValueError(f"not a Cobertura coverage report (root <{root.tag}>)")
    return Coverage(
        line_rate=float(root.get("line-rate") or 0.0),
        branch_rate=float(root.get("branch-rate") or 0.0),
    )
