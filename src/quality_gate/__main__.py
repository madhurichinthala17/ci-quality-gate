"""Enables `python -m quality_gate ...` — what the CI workflow invokes."""

from __future__ import annotations

import sys

from .cli import main

sys.exit(main())
