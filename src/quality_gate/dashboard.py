"""Release-metrics dashboard — feeds Allure and a companion trend page.

Allure natively trends test outcomes (pass/fail/flaky). The three *business*
metrics on the resume dashboard — coverage %, flake rate, defect-escape rate —
are not test outcomes, so we accumulate them here in a metrics history, surface
the current values into the Allure report via `environment.properties`, and
render their week-over-week trend as a small companion HTML page.

Pure file I/O — no Allure Java CLI and no browser needed, so it's fully testable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .gate.report import GateReport


@dataclass
class Metrics:
    timestamp: str
    coverage_pct: float
    flake_rate: float
    escape_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


def metrics_from_gate(report: GateReport) -> Metrics:
    """Extract the three dashboard metrics from the gate's check results."""
    by_name = {c.name: c.metrics for c in report.checks}
    return Metrics(
        timestamp=datetime.now(timezone.utc).isoformat(),
        coverage_pct=by_name.get("coverage", {}).get("line_pct", 0.0),
        flake_rate=by_name.get("flake_rate", {}).get("flake_rate", 0.0),
        escape_rate=by_name.get("defect_escape", {}).get("escape_rate", 0.0),
    )


def update_history(history_path: str, metrics: Metrics) -> list[dict]:
    """Append this run's metrics to the rolling history file; return the full list."""
    path = Path(history_path)
    history = json.loads(path.read_text()) if path.exists() else []
    history.append(metrics.to_dict())
    path.write_text(json.dumps(history, indent=2))
    return history


def write_environment(allure_dir: str, metrics: Metrics) -> None:
    """Surface current metrics into the Allure report's Environment widget."""
    directory = Path(allure_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "environment.properties").write_text(
        f"coverage_pct={metrics.coverage_pct:.2f}\n"
        f"flake_rate={metrics.flake_rate:.3f}\n"
        f"defect_escape_rate={metrics.escape_rate:.3f}\n"
    )


_TREND_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Quality Gate — release metrics trend</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>Release quality trend (week over week)</h1>
  <canvas id="trend"></canvas>
  <script>
    const data = __DATA__;
    const labels = data.map(d => d.timestamp);
    new Chart(document.getElementById('trend'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {label: 'coverage %', data: data.map(d => d.coverage_pct)},
          {label: 'flake rate', data: data.map(d => d.flake_rate)},
          {label: 'defect escape rate', data: data.map(d => d.escape_rate)},
        ],
      },
    });
  </script>
</body>
</html>
"""


def write_trend_page(out_path: str, history: list[dict]) -> None:
    """Render the three-metric trend as a standalone HTML page."""
    html = _TREND_TEMPLATE.replace("__DATA__", json.dumps(history))
    Path(out_path).write_text(html, encoding="utf-8")


def publish(
    report: GateReport,
    allure_dir: str,
    history_path: str = "metrics-history.json",
    trend_path: str = "metrics-trend.html",
) -> Metrics:
    """Update history, write Allure environment, and render the trend page."""
    metrics = metrics_from_gate(report)
    history = update_history(history_path, metrics)
    write_environment(allure_dir, metrics)
    write_trend_page(trend_path, history)
    return metrics
