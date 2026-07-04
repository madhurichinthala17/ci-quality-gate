"""FakeProvider + cost-estimate tests (offline, deterministic)."""

from __future__ import annotations

from quality_gate.triage.models import TriageCategory
from quality_gate.triage.prompt import parse_ticket
from quality_gate.triage.provider import FakeProvider, estimate_cost


def test_fake_provider_classifies_timeout():
    resp = FakeProvider().complete("sys", "Type: TimeoutError\nrequest exceeded 5s")
    ticket = parse_ticket(resp.text, "t::a")
    assert ticket.category is TriageCategory.TIMEOUT
    assert resp.output_tokens > 0


def test_fake_provider_unknown_when_no_signal():
    resp = FakeProvider().complete("sys", "something inscrutable")
    assert parse_ticket(resp.text, "t::a").category is TriageCategory.UNKNOWN


def test_estimate_cost():
    assert estimate_cost("fake-1", 1000, 1000) == 0.0
    # 1M input @ $5 + 1M output @ $25 = $30
    assert estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0
