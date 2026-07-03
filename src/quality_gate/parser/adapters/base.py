"""The adapter contract every test-report format implements.

This is the seam that keeps the system format-agnostic. The dispatcher sniffs a
file's XML root with `can_parse()`, then hands the file to the first adapter that
recognizes it. Supporting a new format (NUnit3 XML, TRX, ...) means writing one
class that satisfies this Protocol and registering it — no stage downstream of
the parser changes.

A Protocol (not a base class) is used on purpose: an adapter only needs the right
*shape*, not an inheritance relationship. That keeps coupling low.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from xml.etree.ElementTree import Element

from ..models import TestRun


@runtime_checkable
class ResultAdapter(Protocol):
    name: str

    def can_parse(self, root: Element) -> bool:
        """Return True if this adapter recognizes the given XML root element."""
        ...

    def parse(self, path: str | Path) -> TestRun:
        """Read the report at `path` into a normalized TestRun."""
        ...
