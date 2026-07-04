"""CLI tests — exercise the exit-code contract end to end against the fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from quality_gate.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


def _invoke(tmp_path, junit, extra=None):
    argv = [
        "--junit",
        str(SAMPLE / junit),
        "--coverage",
        str(SAMPLE / "coverage.xml"),
        "--history",
        str(tmp_path / "h.db"),
        "--report",
        str(tmp_path / "r.json"),
        *(extra or []),
    ]
    rc = main(argv)
    report = json.loads((tmp_path / "r.json").read_text())
    return rc, report


def test_passing_run_exits_zero(tmp_path):
    rc, report = _invoke(tmp_path, "all_pass.xml")
    assert rc == 0
    assert report["verdict"] == "pass"


def test_real_failure_exits_one(tmp_path):
    rc, report = _invoke(tmp_path, "assertion_failure.xml")
    assert rc == 1
    assert report["verdict"] == "fail"


def test_coverage_below_override_exits_one(tmp_path):
    # fixture is 87.3%; demand 95% -> coverage FAIL even with all tests passing
    rc, report = _invoke(tmp_path, "all_pass.xml", extra=["--min-coverage", "95"])
    assert rc == 1
    assert report["verdict"] == "fail"
