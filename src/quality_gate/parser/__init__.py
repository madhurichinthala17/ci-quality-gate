"""Public parser API.

`parse_report(path)` reads any supported test report into a normalized TestRun,
auto-detecting the format via the registered adapters. This is the only entry
point the rest of the system uses; nothing else imports an adapter directly.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import parse as et_parse

from .adapters import ADAPTERS
from .models import Status, TestResult, TestRun

__all__ = ["parse_report", "UnsupportedReportError", "Status", "TestResult", "TestRun"]


class UnsupportedReportError(ValueError):
    """No registered adapter recognized the report file."""


def parse_report(path: str | Path) -> TestRun:
    # Sniff the root once to choose an adapter. The chosen adapter re-parses the
    # file itself (keeps `parse(path)` self-contained); the double read is
    # negligible for CI-sized reports.
    root = et_parse(path).getroot()
    for adapter in ADAPTERS:
        if adapter.can_parse(root):
            return adapter.parse(path)
    raise UnsupportedReportError(
        f"No adapter recognizes report '{path}' (root <{root.tag}>). "
        f"Known formats: {[a.name for a in ADAPTERS]}."
    )
