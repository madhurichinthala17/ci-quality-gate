"""Triage orchestration — wraps the pure pieces with the production behaviors.

Dedupe (identical failures cost one call), cost cap (stop when spend hits the
limit), graceful degradation (a provider error never propagates), and token/cost
observability. It classifies and explains; it never touches the gate verdict.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from ..parser.models import TestResult
from .config import TriageConfig
from .models import Ticket, TriageReport
from .prompt import build_prompt, parse_ticket
from .provider import LLMProvider, estimate_cost


def _signature(test: TestResult) -> str:
    """Group tests that fail the same way, so identical failures cost one call."""
    return f"{test.type or 'none'}::{(test.message or '').strip()[:120]}"


def triage_tests(
    tests: Sequence[TestResult],
    provider: LLMProvider,
    config: TriageConfig | None = None,
) -> TriageReport:
    config = config or TriageConfig()
    report = TriageReport()
    report.cost.provider = provider.name
    report.cost.model = provider.model
    seen: dict[str, Ticket] = {}  # signature -> Ticket (dedupe cache)

    for i, test in enumerate(tests):
        signature = _signature(test)
        if signature in seen:
            report.cost.deduped += 1
            report.tickets.append(replace(seen[signature], test_id=test.id))
            continue

        if report.cost.usd >= config.max_cost_usd:
            report.skipped.append(test.id)
            continue

        system, user = build_prompt(test, config.detail_char_limit)
        try:
            resp = provider.complete(system, user)
        except Exception as exc:  # any provider failure degrades gracefully
            report.degraded = True
            report.degraded_reason = f"{type(exc).__name__}: {exc}"
            report.skipped.extend(t.id for t in tests[i:])
            break

        report.cost.add(
            resp.input_tokens,
            resp.output_tokens,
            estimate_cost(provider.model, resp.input_tokens, resp.output_tokens),
        )
        ticket = parse_ticket(resp.text, test.id)
        seen[signature] = ticket
        report.tickets.append(ticket)

    return report
