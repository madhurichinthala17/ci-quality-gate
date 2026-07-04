"""CLI + dashboard integration — --allure-dir triggers metric artifacts."""

from __future__ import annotations

from pathlib import Path

from quality_gate.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


def test_allure_dir_writes_dashboard_artifacts(tmp_path):
    allure = tmp_path / "allure-results"
    history = tmp_path / "metrics-history.json"
    trend = tmp_path / "metrics-trend.html"
    main([
        "--junit", str(SAMPLE / "all_pass.xml"),
        "--coverage", str(SAMPLE / "coverage.xml"),
        "--history", str(tmp_path / "h.db"),
        "--report", str(tmp_path / "gate.json"),
        "--allure-dir", str(allure),
        "--metrics-history", str(history),
        "--trend-report", str(trend),
    ])
    assert (allure / "environment.properties").exists()
    assert history.exists()
    assert trend.exists()


def test_no_allure_dir_means_no_dashboard(tmp_path):
    trend = tmp_path / "metrics-trend.html"
    main([
        "--junit", str(SAMPLE / "all_pass.xml"),
        "--coverage", str(SAMPLE / "coverage.xml"),
        "--history", str(tmp_path / "h.db"),
        "--report", str(tmp_path / "gate.json"),
        "--trend-report", str(trend),
    ])
    assert not trend.exists()  # dashboard only runs when --allure-dir is set
