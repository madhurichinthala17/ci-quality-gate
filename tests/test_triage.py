"""Triage orchestrator tests — dedupe, cost cap, graceful degradation (all offline)."""

from __future__ import annotations

from quality_gate.parser.models import Status, TestResult
from quality_gate.triage import FakeProvider, TriageCategory, TriageConfig, triage_tests
from quality_gate.triage.provider import LLMResponse


def _fail(test_id: str, type_: str, message: str) -> TestResult:
    c, n = test_id.split("::")
    return TestResult(
        id=test_id,
        name=n,
        classname=c,
        suite="s",
        status=Status.FAILED,
        duration=0.0,
        message=message,
        detail=message,
        type=type_,
    )


def test_produces_one_ticket_per_test():
    tests = [
        _fail("t::a", "TimeoutError", "timed out"),
        _fail("t::b", "AssertionError", "assert 1 == 2"),
    ]
    report = triage_tests(tests, FakeProvider())
    assert not report.degraded
    cats = {t.test_id: t.category for t in report.tickets}
    assert cats["t::a"] is TriageCategory.TIMEOUT
    assert cats["t::b"] is TriageCategory.ASSERTION
    assert report.cost.calls == 2


def test_dedupes_identical_failures():
    # same type + message -> one LLM call, two tickets (reused per test_id)
    tests = [_fail("t::a", "TimeoutError", "timed out"), _fail("t::b", "TimeoutError", "timed out")]
    report = triage_tests(tests, FakeProvider())
    assert report.cost.calls == 1
    assert report.cost.deduped == 1
    assert len(report.tickets) == 2
    assert {t.test_id for t in report.tickets} == {"t::a", "t::b"}


class _PricyProvider:
    name = "pricy"
    model = "gpt-4o"

    def complete(self, system: str, user: str) -> LLMResponse:
        # ~$2.50 per call at gpt-4o prices -> exceeds a small cap immediately
        return LLMResponse(
            '{"category":"unknown","probable_cause":"c","suggested_next_step":"s","grounded":false}',
            input_tokens=200_000,
            output_tokens=200_000,
        )


def test_cost_cap_skips_remaining():
    tests = [_fail("t::a", "E", "one"), _fail("t::b", "E", "two"), _fail("t::c", "E", "three")]
    report = triage_tests(tests, _PricyProvider(), TriageConfig(max_cost_usd=0.50))
    assert report.cost.calls == 1  # only the first call happened
    assert report.skipped == ["t::b", "t::c"]  # cap stopped the rest


class _BoomProvider:
    name = "boom"
    model = "fake-1"

    def complete(self, system: str, user: str) -> LLMResponse:
        raise RuntimeError("api down")


def test_provider_failure_degrades_without_raising():
    tests = [_fail("t::a", "E", "one"), _fail("t::b", "E", "two")]
    report = triage_tests(tests, _BoomProvider())  # must not raise
    assert report.degraded
    assert "RuntimeError" in report.degraded_reason
    assert report.tickets == []
    assert report.skipped == ["t::a", "t::b"]
