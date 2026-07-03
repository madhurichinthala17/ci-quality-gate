"""Parser tests, run against the labelled fixtures in sample_data/.

Each fixture was authored to exercise a specific parser path (see sample_data).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quality_gate.parser import Status, UnsupportedReportError, parse_report

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"
READ_PATIENT = "tests.test_patient::test_read_patient"


def test_all_pass_reads_passes_and_ids():
    run = parse_report(SAMPLE / "all_pass.xml")
    assert len(run) == 3
    assert all(r.status is Status.PASSED for r in run.results)
    assert run.failing == []
    assert READ_PATIENT in {r.id for r in run.results}  # stable classname::name key


def test_assertion_failure_extracts_message_type_detail():
    run = parse_report(SAMPLE / "assertion_failure.xml")
    assert run.count(Status.FAILED) == 1
    (failed,) = run.failing
    assert failed.id == READ_PATIENT
    assert failed.type == "AssertionError"
    assert failed.message == "assert 404 == 200"
    assert "status_code == 200" in failed.detail


def test_error_and_skip_are_distinct_and_skip_is_not_failing():
    run = parse_report(SAMPLE / "error_and_skip.xml")
    assert run.count(Status.ERROR) == 1
    assert run.count(Status.SKIPPED) == 1
    # a skip must NOT count as failing — this is what protects flake math later
    (failing,) = run.failing
    assert failing.status is Status.ERROR
    assert failing.type == "TimeoutError"


def test_same_test_flips_across_runs():
    # sets up the flake demo: identical id, different outcome across builds
    passed = next(r for r in parse_report(SAMPLE / "all_pass.xml").results if r.id == READ_PATIENT)
    failed = next(r for r in parse_report(SAMPLE / "assertion_failure.xml").results if r.id == READ_PATIENT)
    assert passed.status is Status.PASSED
    assert failed.status is Status.FAILED


def test_unknown_format_is_rejected_cleanly(tmp_path):
    # a bare NUnit3-style root — no adapter claims it, so we fail loudly
    nunit = tmp_path / "nunit.xml"
    nunit.write_text('<?xml version="1.0"?><test-run id="2"><test-case name="x"/></test-run>')
    with pytest.raises(UnsupportedReportError):
        parse_report(nunit)
