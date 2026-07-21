"""Tests for collection-native exasol_script runtime helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from exasol.ansible_modules import exasol_script


class FakeStatement:
    """Small pyexasol statement stand-in for helper-level tests."""

    def __init__(
        self,
        query: str,
        rows: list[Any] | None = None,
        result_type: str = "resultSet",
        rowcount: int = 0,
        execution_time: float = 0.0,
        column_names: list[str] | None = None,
    ) -> None:
        self.query = query
        self._rows = rows or []
        self.result_type = result_type
        self._rowcount = rowcount
        self.execution_time = execution_time
        self.col_names = column_names or []

    def fetchall(self) -> list[Any]:
        return self._rows

    def rowcount(self) -> int:
        return self._rowcount

    def column_names(self) -> list[str]:
        return self.col_names


class FakeConnection:
    """Small pyexasol connection stand-in exposing execute_sql_script."""

    def __init__(self, statements: list[FakeStatement]) -> None:
        self._statements = statements
        self.executed_scripts: list[str] = []

    def execute_sql_script(self, script: str) -> list[FakeStatement]:
        self.executed_scripts.append(script)
        return self._statements


def test_module_argument_spec_includes_script_option() -> None:
    """Verify the script runtime exposes a single required string option."""
    argument_spec = exasol_script.module_argument_spec()

    assert argument_spec["script"] == {"type": "str", "required": True}
    assert "positional_args" not in argument_spec
    assert "named_args" not in argument_spec
    assert argument_spec["login_password"]["no_log"] is True


def test_connection_argument_spec_is_shared_with_query_module() -> None:
    """Verify the script module reuses the shared connection argument spec."""
    argument_spec = exasol_script.exasol_connection_argument_spec()

    assert argument_spec["login_password"]["no_log"] is True
    assert argument_spec["client_kwargs"]["no_log"] is True


def test_execute_script_returns_design_doc_result_shape() -> None:
    """Verify script execution returns the collection's public result contract."""
    connection = FakeConnection(
        [
            FakeStatement(
                query="SELECT 1 AS A",
                rows=[{"A": Decimal("1.5")}],
                rowcount=1,
                execution_time=0.001,
            ),
            FakeStatement(
                query="CREATE SCHEMA T",
                rows=[],
                result_type="rowCount",
                rowcount=0,
                execution_time=0.002,
            ),
        ]
    )

    result = exasol_script.execute_script(connection, "SELECT 1 AS A; CREATE SCHEMA T;")

    assert result == {
        "changed": True,
        "query_result": [],
        "query_all_results": [
            [{"A": "1.5"}],
            [],
        ],
        "executed_queries": ["SELECT 1 AS A", "CREATE SCHEMA T"],
        "rowcount": [1, 0],
        "execution_time_ms": [1.0, 2.0],
    }
    assert connection.executed_scripts == ["SELECT 1 AS A; CREATE SCHEMA T;"]


def test_execute_script_reports_unchanged_for_read_only_script() -> None:
    """Verify a script made up only of read-only statements is unchanged."""
    connection = FakeConnection(
        [
            FakeStatement(query="SELECT 1 AS A", rows=[{"A": 1}], rowcount=1),
            FakeStatement(query="SELECT 2 AS B", rows=[{"B": 2}], rowcount=1),
        ]
    )

    result = exasol_script.execute_script(connection, "SELECT 1 AS A; SELECT 2 AS B;")

    assert result["changed"] is False
    assert result["query_result"] == [{"B": 2}]


def test_execute_script_handles_script_body_statement() -> None:
    """Verify a single script-body statement, as split by pyexasol, is reported as-is."""
    script_body_statement = (
        "CREATE OR REPLACE PYTHON3 SCALAR SCRIPT demo.double_value(x DOUBLE)\n"
        "RETURNS DOUBLE AS\n"
        "def run(ctx):\n"
        "    x = ctx.x; return x * 2"
    )
    connection = FakeConnection(
        [FakeStatement(query=script_body_statement, result_type="rowCount")]
    )

    result = exasol_script.execute_script(connection, script_body_statement + "\n/\n")

    assert result["changed"] is True
    assert result["executed_queries"] == [script_body_statement]


def test_check_mode_result_returns_none_for_read_only_script() -> None:
    """Verify a read-only script does not produce a synthetic check-mode result."""
    assert exasol_script.check_mode_result("SELECT 1;\nSELECT 2;") is None


def test_check_mode_result_predicts_write_without_execution() -> None:
    """Verify a write script produces one predicted entry for the whole script."""
    script = "SELECT 1;\nCREATE SCHEMA demo;"

    assert exasol_script.check_mode_result(script) == {
        "changed": True,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": [script],
        "rowcount": [],
        "execution_time_ms": [],
    }


def test_run_script_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify script execution is routed through the runtime connection helper."""
    params: dict[str, object] = {"script": "SELECT 1 AS A;"}
    connection = object()

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_script,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_script,
        "execute_script",
        lambda passed_connection, script: {
            "connection": passed_connection,
            "script": script,
        },
    )

    result = exasol_script.run_script(params)

    assert result == {
        "connection": connection,
        "script": "SELECT 1 AS A;",
    }


def test_error_sanitization_redacts_login_password() -> None:
    """Verify failures do not leak known secret values."""
    message = exasol_script.sanitize_error_message(
        RuntimeError("bad password swordfish"),
        {"login_password": "swordfish"},
    )

    assert message == "bad password ********"
