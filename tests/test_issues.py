"""Ticket-filing tests — the gh-free paths (no network, no gh CLI needed)."""

from __future__ import annotations

import json

from quality_gate.issues import _issue_title, file_tickets


def test_missing_report_is_noop(tmp_path):
    assert file_tickets(str(tmp_path / "nope.json")) == 0


def test_empty_tickets_is_noop(tmp_path):
    report = tmp_path / "triage.json"
    report.write_text(json.dumps({"tickets": []}))
    assert file_tickets(str(report)) == 0  # returns before touching gh


def test_issue_title_format():
    assert _issue_title({"test_id": "t::a", "category": "timeout"}) == "[quality-gate] t::a (timeout)"
