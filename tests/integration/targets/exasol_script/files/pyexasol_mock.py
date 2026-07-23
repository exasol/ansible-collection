"""exasol_script-specific pyexasol mock scenarios."""

from __future__ import annotations

from typing import Any

from pyexasol_mock_base import (
    MockConnection,
    MockStatement,
    connect_with_handlers,
    public_connect_kwargs,
    result_statement,
)

STATEMENT_HANDLERS = {
    "SELECT MOCK_CONNECTION_KWARGS": lambda connection, _query, _params: (
        connection_kwargs_statement(connection)
    ),
    "SELECT 1 AS A": lambda _connection, _query, _params: (
        result_statement(rows=[{"A": 1}])
    ),
    "SELECT 2 AS B": lambda _connection, _query, _params: (
        result_statement(rows=[{"B": 2}])
    ),
}

QUERY_ERRORS = {
    "MOCK_RAISE_SECRET": "script failed with password swordfish",
}

AUTHENTICATION_ERRORS = {
    "bad-secret": "authentication failed for password bad-secret",
}


def connect(**kwargs: Any) -> MockConnection:
    """Return an exasol_script-specific mock Exasol connection."""
    return connect_with_handlers(
        connect_kwargs=kwargs,
        statement_handlers=STATEMENT_HANDLERS,
        authentication_errors=AUTHENTICATION_ERRORS,
        query_errors=QUERY_ERRORS,
    )


def connection_kwargs_statement(connection: MockConnection) -> MockStatement:
    return result_statement(
        rows=[{"KWARGS": public_connect_kwargs(connection.connect_kwargs)}],
    )
