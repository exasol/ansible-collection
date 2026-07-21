"""Tests for Exasol info runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_info


def _normalize_query(query: str) -> str:
    return " ".join(query.split())


class FakeStatement:
    """Small pyexasol statement stand-in for info runtime tests."""

    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        result_type: str = "resultSet",
    ) -> None:
        self._rows = rows or []
        self.result_type = result_type
        self.execution_time = 0.001

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows

    def rowcount(self) -> int:
        return len(self._rows)


class FakeConnection:
    """Small pyexasol connection stand-in with deterministic metadata responses."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized_query = _normalize_query(query)
        self.executed.append(normalized_query)

        if normalized_query == _normalize_query(exasol_info.VERSION_QUERY):
            return FakeStatement(rows=[{"VERSION": "8.39.1"}])

        if normalized_query == _normalize_query(exasol_info.DATABASE_NAME_QUERY):
            return FakeStatement(rows=[{"DATABASE_NAME": "EXA_DB"}])

        if normalized_query == _normalize_query(exasol_info.CLUSTER_SIZE_QUERY):
            return FakeStatement(rows=[{"CLUSTER_SIZE": 1}])

        raise RuntimeError(f"unexpected query: {query}")


def test_module_argument_spec_matches_shared_connection_options() -> None:
    """Verify the info runtime only exposes the shared connection parameters."""
    argument_spec = exasol_info.module_argument_spec()

    assert argument_spec["login_user"]["required"] is True
    assert argument_spec["login_password"]["no_log"] is True
    assert "query" not in argument_spec
    assert "name" not in argument_spec


# [utest -> dsn~exasol-info-read-only-metadata-retrieval~1]
def test_ensure_info_returns_basic_server_metadata() -> None:
    """Verify the info runtime returns version, database, and cluster size."""
    connection = FakeConnection()

    result = exasol_info.ensure_info(connection)

    assert result == {
        "changed": False,
        "version": "8.39.1",
        "database_name": "EXA_DB",
        "cluster_size": 1,
    }
    assert connection.executed == [
        _normalize_query(exasol_info.VERSION_QUERY),
        _normalize_query(exasol_info.DATABASE_NAME_QUERY),
        _normalize_query(exasol_info.CLUSTER_SIZE_QUERY),
    ]


def test_ensure_info_uses_cluster_size_query() -> None:
    """Verify cluster-size lookup uses the current cluster metadata source."""
    connection = FakeConnection()

    result = exasol_info.ensure_info(connection)

    assert result["cluster_size"] == 1
    assert connection.executed[-1] == _normalize_query(exasol_info.CLUSTER_SIZE_QUERY)


def test_run_info_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify info execution is routed through the runtime connection helper."""
    connection = object()
    params = {"login_user": "sys"}

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_info.common_query,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_info,
        "ensure_info",
        lambda passed_connection: {
            "connection": passed_connection,
        },
    )

    assert exasol_info.run_info(params) == {
        "connection": connection,
    }
