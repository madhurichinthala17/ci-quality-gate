"""Build-history persistence — the I/O adapter layer for flake detection.

`HistoryStore` is the interface (port) the engine depends on. Two adapters implement
it: `SqliteHistoryStore` (a local file, zero setup) and `LibSqlHistoryStore` (Turso /
libSQL in the cloud, durable across CI runs). Because libSQL speaks SQLite's dialect,
both adapters share all their SQL via `_SqlHistoryStore`; they differ only in how the
connection is opened. The engine, detector, and gate never change.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from ..parser.models import Status, TestRun


class HistoryStore(Protocol):
    """What the engine needs from persistence — no storage details leak here."""

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
    return datetime.now(UTC).isoformat()


class _SqlHistoryStore:
    """Shared SQL over a sqlite3-compatible connection (stdlib sqlite3 or libSQL).

    Subclasses set ``self._conn`` in __init__, then call ``self._apply_schema()``.
    Every method below is dialect-identical, so the local and cloud adapters differ
    only in how they connect. ``_conn`` is typed ``Any`` because it may be either a
    ``sqlite3.Connection`` or a libSQL connection — both expose the same DB-API surface.
    """

    _conn: Any

    def _apply_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> _SqlHistoryStore:
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
        build_ord = cur.lastrowid
        assert build_ord is not None  # the driver sets lastrowid after an INSERT
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


class SqliteHistoryStore(_SqlHistoryStore):
    """SQLite-backed history — a single file on disk, zero setup. Implements HistoryStore."""

    def __init__(self, db_path: str | Path = "gate-history.db") -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._apply_schema()


class LibSqlHistoryStore(_SqlHistoryStore):
    """Turso / libSQL-backed history — durable across CI runs. Implements HistoryStore.

    libSQL speaks SQLite's dialect, so all SQL is inherited unchanged; only the
    connection differs (a remote URL + auth token instead of a local file).
    Credentials are passed in by the caller (the CLI reads them from the environment)
    and are never hardcoded or logged.
    """

    def __init__(self, url: str, auth_token: str) -> None:
        import libsql  # lazy: the optional 'turso' extra, only needed for cloud history

        # Remote-only: every query hits Turso directly — no local replica to sync,
        # which suits an ephemeral CI runner.
        self._conn = libsql.connect(database=url, auth_token=auth_token)
        self._apply_schema()
