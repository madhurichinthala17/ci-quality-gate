"""HistoryStore tests — persistence and windowing, on a temp SQLite file."""

from __future__ import annotations

from quality_gate.flake.store import LibSqlHistoryStore, SqliteHistoryStore
from quality_gate.parser.models import Status, TestResult, TestRun


def _run(test_id: str, status: Status) -> TestRun:
    classname, name = test_id.split("::")
    return TestRun(
        [
            TestResult(
                id=test_id, name=name, classname=classname, suite="s", status=status, duration=0.0
            )
        ]
    )


def test_record_and_window_newest_first(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    store.record_run(_run("t::a", Status.PASSED))
    store.record_run(_run("t::a", Status.FAILED))
    store.record_run(_run("t::a", Status.PASSED))

    assert store.window("t::a", 10) == [Status.PASSED, Status.FAILED, Status.PASSED]
    assert store.window("t::a", 1) == [Status.PASSED]  # newest only
    assert store.window("t::missing", 10) == []  # unknown test


def test_window_is_per_test(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    store.record_run(_run("t::a", Status.FAILED))
    store.record_run(_run("t::b", Status.PASSED))
    assert store.window("t::a", 10) == [Status.FAILED]
    assert store.window("t::b", 10) == [Status.PASSED]


def test_quarantine_roundtrip_is_idempotent(tmp_path):
    store = SqliteHistoryStore(tmp_path / "h.db")
    assert store.quarantined() == set()
    store.quarantine("t::a")
    store.quarantine("t::a")  # inserting twice is a no-op
    assert store.quarantined() == {"t::a"}
    store.release("t::a")
    assert store.quarantined() == set()


def test_libsql_store_runs_the_same_sql_in_memory():
    """The Turso adapter shares all SQL with the SQLite one; ':memory:' exercises the
    real libSQL driver offline, so this proves the cloud store behaves identically
    without needing a Turso account or network."""
    store = LibSqlHistoryStore(":memory:", "dummy-token")  # token ignored for a local db
    store.record_run(_run("t::a", Status.PASSED))
    store.record_run(_run("t::a", Status.FAILED))
    assert store.window("t::a", 10) == [Status.FAILED, Status.PASSED]  # newest first
    assert store.all_test_ids() == ["t::a"]

    store.quarantine("t::a")
    assert store.quarantined() == {"t::a"}
    store.release("t::a")
    assert store.quarantined() == set()
