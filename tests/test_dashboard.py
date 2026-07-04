"""Dashboard tests — metrics extraction, history accumulation, Allure env, trend page."""

from __future__ import annotations

import json

from quality_gate.dashboard import (
    Metrics,
    metrics_from_gate,
    publish,
    update_history,
    write_environment,
    write_trend_page,
)
from quality_gate.gate.report import CheckResult, GateReport, Verdict


def _report(cov: float, flake: float, escape: float) -> GateReport:
    return GateReport(Verdict.PASS, [
        CheckResult("coverage", Verdict.PASS, "", {"line_pct": cov}),
        CheckResult("flake_rate", Verdict.PASS, "", {"flake_rate": flake}),
        CheckResult("defect_escape", Verdict.PASS, "", {"escape_rate": escape}),
    ])


def test_metrics_extracted_from_gate():
    m = metrics_from_gate(_report(95.3, 0.10, 0.05))
    assert (m.coverage_pct, m.flake_rate, m.escape_rate) == (95.3, 0.10, 0.05)


def test_history_accumulates_across_runs(tmp_path):
    hp = str(tmp_path / "metrics-history.json")
    update_history(hp, Metrics("t1", 90.0, 0.0, 0.0))
    history = update_history(hp, Metrics("t2", 95.0, 0.1, 0.02))
    assert len(history) == 2
    assert json.loads((tmp_path / "metrics-history.json").read_text())[1]["coverage_pct"] == 95.0


def test_environment_properties_written(tmp_path):
    write_environment(str(tmp_path), Metrics("t", 87.34, 0.20, 0.05))
    text = (tmp_path / "environment.properties").read_text()
    assert "coverage_pct=87.34" in text
    assert "flake_rate=0.200" in text
    assert "defect_escape_rate=0.050" in text


def test_trend_page_embeds_data(tmp_path):
    out = tmp_path / "trend.html"
    write_trend_page(str(out), [{"timestamp": "t", "coverage_pct": 90, "flake_rate": 0, "escape_rate": 0}])
    html = out.read_text()
    assert "Chart" in html          # chart library referenced
    assert "coverage_pct" in html   # data embedded


def test_publish_writes_all_three_artifacts(tmp_path):
    m = publish(
        _report(88.0, 0.1, 0.02),
        allure_dir=str(tmp_path / "allure-results"),
        history_path=str(tmp_path / "metrics-history.json"),
        trend_path=str(tmp_path / "metrics-trend.html"),
    )
    assert (tmp_path / "allure-results" / "environment.properties").exists()
    assert (tmp_path / "metrics-history.json").exists()
    assert (tmp_path / "metrics-trend.html").exists()
    assert m.coverage_pct == 88.0
