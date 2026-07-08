"""CLI tests — exercise the exit-code contract end to end against the fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quality_gate.cli import _make_store, main
from quality_gate.flake.store import LibSqlHistoryStore, SqliteHistoryStore

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


def _invoke(tmp_path, junit, extra=None):
    argv = [
        "--junit",
        str(SAMPLE / junit),
        "--coverage",
        str(SAMPLE / "coverage.xml"),
        "--history",
        str(tmp_path / "h.db"),
        "--report",
        str(tmp_path / "r.json"),
        *(extra or []),
    ]
    rc = main(argv)
    report = json.loads((tmp_path / "r.json").read_text())
    return rc, report


def test_passing_run_exits_zero(tmp_path):
    rc, report = _invoke(tmp_path, "all_pass.xml")
    assert rc == 0
    assert report["verdict"] == "pass"


def test_real_failure_exits_one(tmp_path):
    rc, report = _invoke(tmp_path, "assertion_failure.xml")
    assert rc == 1
    assert report["verdict"] == "fail"


def test_coverage_below_override_exits_one(tmp_path):
    # fixture is 87.3%; demand 95% -> coverage FAIL even with all tests passing
    rc, report = _invoke(tmp_path, "all_pass.xml", extra=["--min-coverage", "95"])
    assert rc == 1
    assert report["verdict"] == "fail"


# --- history backend selection (_make_store) ---------------------------------


def test_make_store_defaults_to_local_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    store = _make_store(str(tmp_path / "h.db"), history_url=None)
    assert isinstance(store, SqliteHistoryStore)


def test_make_store_uses_turso_when_url_and_token_present(monkeypatch):
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "dummy-token")
    # ':memory:' as the URL exercises the real libSQL driver without a network call
    store = _make_store("unused.db", history_url=":memory:")
    assert isinstance(store, LibSqlHistoryStore)


def test_make_store_url_without_token_fails_loudly(monkeypatch):
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        _make_store("unused.db", history_url="libsql://example.turso.io")
