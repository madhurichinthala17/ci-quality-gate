"""Command-line entry point — the composition root.

Wires parse -> flake evaluate -> gate, writes the JSON report, prints a summary,
and returns a non-zero exit code when the gate blocks (the CI integration contract).
This is the only module that constructs concrete implementations (e.g. the SQLite
store); everything below it depends on interfaces.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .flake import SqliteHistoryStore, evaluate
from .gate import GateConfig, parse_coverage, run_gate
from .gate.report import GateReport, Verdict
from .parser import parse_report


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="quality-gate",
        description="AI-powered CI/CD quality gate: parse tests, detect flakes, decide pass/fail.",
    )
    p.add_argument("--junit", required=True, help="Path to the JUnit XML test report.")
    p.add_argument("--coverage", help="Path to coverage.xml (Cobertura format). Optional.")
    p.add_argument("--history", default="gate-history.db", help="SQLite history DB path.")
    p.add_argument("--build-id", help="Identifier for this build (optional).")
    p.add_argument("--report", default="gate-report.json", help="Where to write the JSON verdict.")
    p.add_argument("--min-coverage", type=float, default=GateConfig.min_coverage,
                   help="Minimum line coverage %% (below this the gate FAILs).")
    p.add_argument("--max-flake-rate", type=float, default=GateConfig.max_flake_rate,
                   help="Max fraction of the suite quarantined before the gate FAILs.")
    p.add_argument("--max-escape-rate", type=float, default=GateConfig.max_escape_rate,
                   help="Defect-escape rate above which the gate WARNs.")
    return p


_LABEL = {Verdict.PASS: "PASS", Verdict.WARN: "WARN", Verdict.FAIL: "FAIL"}


def _print_summary(report: GateReport) -> None:
    print(f"Quality Gate: {report.verdict.value.upper()}")
    width = max((len(c.name) for c in report.checks), default=0)
    for c in report.checks:
        print(f"  [{_LABEL[c.status]}] {c.name.ljust(width)}  {c.message}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    run = parse_report(args.junit)
    coverage = parse_coverage(args.coverage) if args.coverage else None
    config = GateConfig(
        min_coverage=args.min_coverage,
        max_flake_rate=args.max_flake_rate,
        max_escape_rate=args.max_escape_rate,
    )

    with SqliteHistoryStore(args.history) as store:
        flake = evaluate(store, run, build_id=args.build_id)
        report = run_gate(run, flake, coverage=coverage, config=config, store=store)

    Path(args.report).write_text(report.to_json())
    _print_summary(report)

    # Exit-code contract: FAIL blocks the CI job; PASS/WARN allow it.
    return 1 if report.blocked else 0


if __name__ == "__main__":
    sys.exit(main())
