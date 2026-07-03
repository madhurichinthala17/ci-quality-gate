"""Format adapters. Register a new one in ADAPTERS and the dispatcher picks it up."""

from __future__ import annotations

from .base import ResultAdapter
from .junit import JUnitAdapter

# The dispatcher tries these in order and uses the first that claims the file.
# Adding NUnit3/TRX later = append one adapter here; nothing else changes.
ADAPTERS: list[ResultAdapter] = [JUnitAdapter()]

__all__ = ["ResultAdapter", "JUnitAdapter", "ADAPTERS"]
