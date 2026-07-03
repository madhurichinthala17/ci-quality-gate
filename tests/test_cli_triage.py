"""CLI + triage integration — offline via FakeProvider, no key or cost."""

from __future__ import annotations

import json
from pathlib import Path

from quality_gate.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


def test_triage_writes_tickets_for_failures(tmp_path):
    triage_out = tmp_path / "triage.json"
    rc = main([
        "--junit", str(SAMPLE / "assertion_failure.xml"),
        "--coverage", str(SAMPLE / "coverage.xml"),
        "--history", str(tmp_path / "h.db"),
        "--report", str(tmp_path / "gate.json"),
        "--triage", "--provider", "fake",
        "--triage-report", str(triage_out),
    ])
    assert rc == 1  # gate still FAILs on the real failure — triage doesn't change that

    tickets = json.loads(triage_out.read_text())["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["test_id"] == "tests.test_patient::test_read_patient"
    assert tickets[0]["category"] == "assertion"  # FakeProvider maps AssertionError -> assertion


def test_no_triage_flag_means_no_triage_file(tmp_path):
    triage_out = tmp_path / "triage.json"
    main([
        "--junit", str(SAMPLE / "all_pass.xml"),
        "--coverage", str(SAMPLE / "coverage.xml"),
        "--history", str(tmp_path / "h.db"),
        "--report", str(tmp_path / "gate.json"),
        "--triage-report", str(triage_out),
    ])
    assert not triage_out.exists()  # triage only runs when --triage is passed
