"""Coverage adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from quality_gate.gate.coverage import parse_coverage

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


def test_parse_coverage_reads_rates():
    cov = parse_coverage(SAMPLE / "coverage.xml")
    assert round(cov.line_pct, 2) == 87.34
    assert round(cov.branch_pct, 2) == 72.0


def test_non_coverage_root_is_rejected(tmp_path):
    bad = tmp_path / "x.xml"
    bad.write_text("<testsuites/>")
    with pytest.raises(ValueError):
        parse_coverage(bad)
