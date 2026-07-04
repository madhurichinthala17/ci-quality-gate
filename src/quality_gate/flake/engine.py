"""Flake orchestration — ties the pure detector to the history store.

Pure wiring: no SQL, no classification math. It records a build, then applies the
quarantine state transitions (enter when a test becomes flaky, exit when it turns
consistent again) and returns a FlakeReport the gate and ticket-generator consume.

Lives in the orchestration layer: depends on the pure `detector` and the
`HistoryStore` *interface* — never on SQLite directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..parser.models import TestRun
from .detector import WINDOW, Verdict, classify, is_consistent
from .store import HistoryStore


@dataclass
class FlakeReport:
    quarantined: set[str] = field(default_factory=set)  # all currently quarantined
    newly_quarantined: set[str] = field(default_factory=set)  # entered this build
    released: set[str] = field(default_factory=set)  # exited this build
    regressions: set[str] = field(default_factory=set)  # consistent failures — must block
    verdicts: dict[str, Verdict] = field(default_factory=dict)  # per-test classification


def evaluate(store: HistoryStore, run: TestRun, build_id: str | None = None) -> FlakeReport:
    store.record_run(run, build_id)
    quarantined = store.quarantined()
    report = FlakeReport(quarantined=quarantined)

    # Evaluate every test in this run, plus any already-quarantined test, so we
    # can release ones that have recovered even if they weren't run this build.
    for test_id in {r.id for r in run.results} | quarantined:
        window = store.window(test_id, WINDOW)
        verdict = classify(window)
        report.verdicts[test_id] = verdict

        if verdict is Verdict.REGRESSION:
            report.regressions.add(test_id)

        if test_id in quarantined:
            # Release only once the test stops flapping (all-pass or all-fail).
            if is_consistent(window):
                store.release(test_id)
                quarantined.discard(test_id)
                report.released.add(test_id)
        elif verdict is Verdict.FLAKY:
            store.quarantine(test_id)
            quarantined.add(test_id)
            report.newly_quarantined.add(test_id)

    return report
