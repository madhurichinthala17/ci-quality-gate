"""Build-history persistence — the I/O adapter layer for flake detection.

`HistoryStore` is the interface (port) the engine depends on; `SqliteHistoryStore`
is the concrete implementation (adapter). Swapping to Postgres later means writing
another class that satisfies this Protocol — the engine, detector, and gate never
change.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from ..parser.models import Status, TestRun


class HistoryStore(Protocol):
    """What the engine needs from persistence — nothing about SQLite leaks here."""

    def record_run(self, run: TestRun, build_id: str | None = None) -> int: ...
    def window(self, test_id: str, n: int) -> list[Status]: ...
    def all_test_ids(self) -> list[str]: ...
    def quarantined(self) -> set[str]: ...
    def quarantine(self, test_id: str) -> None: ...
    def release(self, test_id: str) -> None: ...


_SCHEMA = """
CREATE TABLE IF NOT EXISTS builds (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id TEXT NOT NULL,
    ts       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_runs (
    build   INTEGER NOT NULL REFERENCES builds(id),
    test_id TEXT NOT NULL,
    status  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_test_runs_test ON test_runs(test_id, build);
CREATE TABLE IF NOT EXISTS quarantine (
    test_id        TEXT PRIMARY KEY,
    quarantined_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteHistoryStore:
    """SQLite-backed history. File-based and zero-infra — just a single file on disk. Implements the HistoryStore interface."""

    def __init__(self, db_path: str | Path = "gate-history.db") -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SqliteHistoryStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def record_run(self, run: TestRun, build_id: str | None = None) -> int:
        """Persist one build's results; returns the build's ordinal id."""
        ts = _now()
        cur = self._conn.execute(
            "INSERT INTO builds(build_id, ts) VALUES (?, ?)",
            (build_id or f"build-{ts}", ts),
        )
        build_ord = int(cur.lastrowid)
        self._conn.executemany(
            "INSERT INTO test_runs(build, test_id, status) VALUES (?, ?, ?)",
            [(build_ord, r.id, r.status.value) for r in run.results],
        )
        self._conn.commit()
        return build_ord

    def window(self, test_id: str, n: int) -> list[Status]:
        """Last `n` statuses for a test, newest first."""
        rows = self._conn.execute(
            "SELECT status FROM test_runs WHERE test_id = ? ORDER BY build DESC LIMIT ?",
            (test_id, n),
        ).fetchall()
        return [Status(row[0]) for row in rows]

    def all_test_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT test_id FROM test_runs").fetchall()
        return [row[0] for row in rows]

    def quarantined(self) -> set[str]:
        rows = self._conn.execute("SELECT test_id FROM quarantine").fetchall()
        return {row[0] for row in rows}

    def quarantine(self, test_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO quarantine(test_id, quarantined_at) VALUES (?, ?)",
            (test_id, _now()),
        )
        self._conn.commit()

    def release(self, test_id: str) -> None:
        self._conn.execute("DELETE FROM quarantine WHERE test_id = ?", (test_id,))
        self._conn.commit()
