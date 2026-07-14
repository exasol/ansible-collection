"""Tests for collection-native exasol_query runtime helpers."""

from __future__ import annotations

import datetime as dt
import json
import ssl
from decimal import Decimal
from typing import Any

import pytest

from exasol.ansible_modules import exasol_query


class FakeStatement:
    """Small pyexasol statement stand-in for helper-level tests."""

    def __init__(
        self,
        rows: list[Any] | None = None,
        result_type: str = "resultSet",
        rowcount: int = 0,
        execution_time: float = 0.0,
        column_names: list[str] | None = None,
    ) -> None:
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
    """Small pyexasol connection stand-in for helper-level tests."""

    def __init__(self, statements: list[FakeStatement]) -> None:
        self.statements = statements
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        self.executed.append((query, query_params))
        return self.statements.pop(0)


def test_connection_argument_spec_marks_secret_options_no_log() -> None:
    """Verify the shared Ansible argument spec protects secret parameters."""
    argument_spec = exasol_query.exasol_connection_argument_spec()

    assert argument_spec["login_password"]["no_log"] is True
    assert argument_spec["client_kwargs"]["no_log"] is True
    assert argument_spec["login_db"]["aliases"] == ["login_schema"]


def test_module_argument_spec_includes_query_specific_options() -> None:
    """Verify the query runtime exposes the full Ansible-facing argument spec."""
    argument_spec = exasol_query.module_argument_spec()

    assert argument_spec["query"] == {"type": "raw", "required": True}
    assert argument_spec["positional_args"] == {"type": "list", "elements": "raw"}
    assert argument_spec["named_args"] == {"type": "dict"}
    assert argument_spec["login_password"]["no_log"] is True


def test_build_exasol_dsn_includes_certificate_fingerprint() -> None:
    """Verify certificate fingerprints are encoded in the pyexasol DSN."""
    dsn = exasol_query.build_exasol_dsn(
        {
            "login_host": "db.example.com",
            "login_port": 8564,
            "certificate_fingerprint": "ABCDEF",
        }
    )

    assert dsn == "db.example.com/ABCDEF:8564"


def test_build_connect_kwargs_maps_design_doc_parameters_to_pyexasol() -> None:
    """Verify collection connection arguments map to pyexasol keyword arguments."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_host": "db.example.com",
            "login_port": 8564,
            "login_user": "sys",
            "login_password": "secret",
            "login_db": "APP",
            "autocommit": False,
            "fetch_size": 8192,
            "compression": True,
            "validate_certs": False,
            "certificate_fingerprint": "ABCDEF",
            "client_kwargs": {
                "client_name": "ansible-test",
                "encryption": False,
                "fetch_dict": False,
                "websocket_sslopt": {"check_hostname": False},
            },
        }
    )

    assert kwargs == {
        "dsn": "db.example.com/ABCDEF:8564",
        "user": "sys",
        "password": "secret",
        "schema": "APP",
        "autocommit": False,
        "fetch_size_bytes": 8192,
        "compression": True,
        "encryption": True,
        "fetch_dict": True,
        "websocket_sslopt": {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False,
        },
        "client_name": "ansible-test",
    }


def test_build_connect_kwargs_applies_design_doc_defaults() -> None:
    """Verify default connection handling, including TLS and fetch dictionaries."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
        }
    )

    assert kwargs["dsn"] == "localhost:8563"
    assert kwargs["schema"] == ""
    assert kwargs["autocommit"] is True
    assert kwargs["fetch_size_bytes"] == 5000
    assert kwargs["compression"] is False
    assert kwargs["encryption"] is True
    assert kwargs["fetch_dict"] is True


def test_build_connect_kwargs_overrides_insecure_websocket_sslopt() -> None:
    """Verify validate_certs=true wins over insecure socket-level overrides."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "client_kwargs": {
                "websocket_sslopt": {
                    "cert_reqs": ssl.CERT_NONE,
                    "check_hostname": False,
                }
            },
        }
    )

    assert kwargs["websocket_sslopt"] == {
        "cert_reqs": ssl.CERT_REQUIRED,
        "check_hostname": False,
    }


def test_build_connect_kwargs_rejects_untrusted_tls_override() -> None:
    """Verify disabling CA validation requires fingerprint pinning."""
    with pytest.raises(ValueError, match="certificate_fingerprint"):
        exasol_query.build_exasol_connect_kwargs(
            {
                "login_user": "sys",
                "login_password": "secret",
                "validate_certs": False,
            }
        )


@pytest.mark.parametrize("fingerprint", ["nocertcheck", "NoCertCheck", " NOCERTCHECK "])
def test_build_connect_kwargs_rejects_nocertcheck_pseudo_fingerprint(
    fingerprint: str,
) -> None:
    """Verify nocertcheck cannot be used as an ersatz trust anchor."""
    with pytest.raises(ValueError, match="nocertcheck"):
        exasol_query.build_exasol_connect_kwargs(
            {
                "login_user": "sys",
                "login_password": "secret",
                "validate_certs": False,
                "certificate_fingerprint": fingerprint,
            }
        )


def test_prepare_query_translates_positional_and_named_args() -> None:
    """Verify Ansible-style placeholders are translated for pyexasol."""
    query, query_params = exasol_query.prepare_query(
        "SELECT ? AS A, :n AS B, '?' AS LITERAL, true::boolean AS FLAG",
        positional_args=[42],
        named_args={"n": 7},
    )

    assert query == (
        "SELECT {__pos_0!d} AS A, {n!d} AS B, '?' AS LITERAL, " "true::boolean AS FLAG"
    )
    assert query_params == {"__pos_0": 42, "n": 7}


def test_execute_queries_returns_design_doc_result_shape() -> None:
    """Verify query execution returns the collection's public result contract."""
    connection = FakeConnection(
        [
            FakeStatement(
                rows=[{"A": Decimal("1.5"), "CREATED_ON": dt.date(2026, 1, 2)}],
                rowcount=1,
                execution_time=0.001,
            ),
            FakeStatement(
                rows=[],
                result_type="rowCount",
                rowcount=0,
                execution_time=0.002,
            ),
        ]
    )

    result = exasol_query.execute_queries(
        connection,
        ["SELECT 1 AS A", "CREATE SCHEMA T"],
    )

    json.dumps(result)

    assert result == {
        "changed": True,
        "query_result": [],
        "query_all_results": [
            [{"A": "1.5", "CREATED_ON": "2026-01-02"}],
            [],
        ],
        "executed_queries": ["SELECT 1 AS A", "CREATE SCHEMA T"],
        "rowcount": [1, 0],
        "execution_time_ms": [1.0, 2.0],
    }
    assert connection.executed == [
        ("SELECT 1 AS A", None),
        ("CREATE SCHEMA T", None),
    ]


def test_tuple_rows_are_returned_as_dictionaries() -> None:
    """Verify tuple rows are mapped with statement column metadata."""
    connection = FakeConnection(
        [
            FakeStatement(
                rows=[(73, "tuple-row")],
                rowcount=1,
                column_names=["ID", "LABEL"],
            ),
        ]
    )

    result = exasol_query.execute_queries(connection, "SELECT 73 AS ID")

    assert result["changed"] is False
    assert result["query_result"] == [{"ID": 73, "LABEL": "tuple-row"}]


def test_error_sanitization_redacts_login_password_and_sensitive_named_args() -> None:
    """Verify failures do not leak known secret values."""
    message = exasol_query.sanitize_error_message(
        RuntimeError("bad password swordfish and value token-value"),
        {
            "login_password": "swordfish",
            "named_args": {"api_token": "token-value"},
        },
    )

    assert message == "bad password ******** and value ********"


def test_error_sanitization_redacts_overlapping_secrets() -> None:
    """Verify overlapping secret values are fully redacted."""
    message = exasol_query.sanitize_error_message(
        RuntimeError("token abcdef password abc"),
        {
            "login_password": "abc",
            "named_args": {"api_token": "abcdef"},
        },
    )

    assert message == "token ******** password ********"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"positional_args": [42]},
        {"named_args": {"name": "app"}},
    ],
)
def test_build_query_request_rejects_bound_args_for_statement_batches(
    kwargs: dict[str, object],
) -> None:
    """Verify statement batches do not ambiguously reuse one argument set."""
    connection = FakeConnection([])

    with pytest.raises(ValueError) as error_info:
        exasol_query.execute_queries(
            connection,
            [
                "SELECT ? AS A",
                "SELECT ? AS B",
            ],
            **kwargs,
        )

    message = str(error_info.value)
    assert "positional_args and named_args" in message
    assert "single SQL statement" in message
    assert "statement batches" in message


def test_check_mode_result_returns_none_for_read_only_queries() -> None:
    """Verify read-only batches do not produce a synthetic check-mode result."""
    assert exasol_query.check_mode_result(["SELECT 1", "SHOW TABLES"]) is None


def test_check_mode_result_predicts_write_without_execution() -> None:
    """Verify write statements produce the public check-mode response shape."""
    assert exasol_query.check_mode_result(["SELECT 1", "CREATE SCHEMA demo"]) == {
        "changed": True,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": ["SELECT 1", "CREATE SCHEMA demo"],
        "rowcount": [],
        "execution_time_ms": [],
    }


def test_run_query_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify query execution is routed through the runtime connection helper."""
    params: dict[str, object] = {
        "query": "SELECT 1 AS A",
        "positional_args": [42],
        "named_args": {"n": 7},
    }
    connection = object()

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_query,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_query,
        "execute_queries",
        lambda passed_connection, query, positional_args=None, named_args=None: {
            "connection": passed_connection,
            "query": query,
            "positional_args": positional_args,
            "named_args": named_args,
        },
    )

    result = exasol_query.run_query(params)

    assert result == {
        "connection": connection,
        "query": "SELECT 1 AS A",
        "positional_args": [42],
        "named_args": {"n": 7},
    }
