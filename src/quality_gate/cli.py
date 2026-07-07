"""Command-line entry point — the composition root.

Wires parse -> flake evaluate -> gate (-> optional LLM triage), writes the JSON
reports, prints a summary, and returns a non-zero exit code when the gate blocks
(the CI integration contract). Triage is advisory and never affects the verdict.
This is the only module that constructs concrete implementations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .flake import SqliteHistoryStore, evaluate
from .gate import GateConfig, parse_coverage, run_gate
from .gate.report import GateReport, Verdict
from .parser import parse_report
from .triage import LLMProvider, TriageConfig, TriageReport, triage_tests


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
    p.add_argument(
        "--min-coverage",
        type=float,
        default=GateConfig.min_coverage,
        help="Minimum line coverage %% (below this the gate FAILs).",
    )
    p.add_argument(
        "--max-flake-rate",
        type=float,
        default=GateConfig.max_flake_rate,
        help="Max fraction of the suite quarantined before the gate FAILs.",
    )
    p.add_argument(
        "--max-escape-rate",
        type=float,
        default=GateConfig.max_escape_rate,
        help="Defect-escape rate above which the gate WARNs.",
    )
    # Triage (advisory — never changes the verdict or exit code)
    p.add_argument(
        "--triage",
        action="store_true",
        help="Run LLM triage on failing tests and write remediation tickets.",
    )
    p.add_argument(
        "--provider",
        choices=["fake", "openai"],
        default="fake",
        help="Triage LLM provider (default: fake, offline).",
    )
    p.add_argument(
        "--triage-model",
        default=None,
        help="Model id for openai; defaults to the provider's own default.",
    )
    p.add_argument(
        "--max-cost-usd",
        type=float,
        default=TriageConfig.max_cost_usd,
        help="Per-run triage cost cap in USD.",
    )
    p.add_argument(
        "--triage-report",
        default="triage-report.json",
        help="Where to write the triage tickets JSON.",
    )
    # Dashboard (optional — writes Allure environment + metrics trend)
    p.add_argument(
        "--allure-dir",
        help="Allure results dir to write dashboard metrics into (enables the dashboard).",
    )
    p.add_argument(
        "--metrics-history",
        default="metrics-history.json",
        help="Rolling release-metrics history JSON.",
    )
    p.add_argument(
        "--trend-report", default="metrics-trend.html", help="Companion metrics-trend HTML page."
    )
    return p


def _make_provider(name: str, model: str | None) -> LLMProvider:
    if name == "openai":
        from .triage import OpenAIProvider

        return OpenAIProvider(model) if model else OpenAIProvider()
    from .triage import FakeProvider

    return FakeProvider()


_LABEL = {Verdict.PASS: "PASS", Verdict.WARN: "WARN", Verdict.FAIL: "FAIL"}


def _print_summary(report: GateReport) -> None:
    print(f"Quality Gate: {report.verdict.value.upper()}")
    width = max((len(c.name) for c in report.checks), default=0)
    for c in report.checks:
        print(f"  [{_LABEL[c.status]}] {c.name.ljust(width)}  {c.message}")


def _print_triage(tr: TriageReport) -> None:
    line = (
        f"Triage ({tr.cost.provider}/{tr.cost.model}): {len(tr.tickets)} ticket(s), "
        f"{tr.cost.calls} call(s), ${tr.cost.usd:.4f}"
    )
    if tr.degraded:
        line += f"  [degraded: {tr.degraded_reason}]"
    print(line)
    for t in tr.tickets:
        print(f"  - {t.test_id} [{t.category.value}] {t.probable_cause}")


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

    if args.triage:
        provider = _make_provider(args.provider, args.triage_model)
        tconfig = TriageConfig(max_cost_usd=args.max_cost_usd)  # model comes from the provider
        triage_report = triage_tests(run.failing, provider, tconfig)
        Path(args.triage_report).write_text(json.dumps(triage_report.to_dict(), indent=2))
        _print_triage(triage_report)

    if args.allure_dir:
        from .dashboard import publish

        publish(report, args.allure_dir, args.metrics_history, args.trend_report)
        print(f"Dashboard: metrics written to {args.allure_dir} + {args.trend_report}")

    # Exit-code contract: FAIL blocks the CI job; PASS/WARN allow it. Triage never affects this.
    return 1 if report.blocked else 0


if __name__ == "__main__":
    sys.exit(main())
