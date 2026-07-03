"""Gate configuration — every tunable threshold in one place.

The composition root (the CLI) constructs this; the checks receive it. Keeping
thresholds here rather than as magic numbers scattered through the logic is what
makes the gate's policy auditable and adjustable in one edit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateConfig:
    min_coverage: float = 80.0     # percent; below this the coverage check FAILs
    max_flake_rate: float = 0.20   # fraction of the suite quarantined; above this FAILs
    max_escape_rate: float = 0.10  # defect-escape rate above this WARNs
    escape_window: int = 20        # builds considered when computing the escape rate
