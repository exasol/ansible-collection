"""exasol_info-specific pyexasol mock scenarios."""

from __future__ import annotations

from typing import Any

from pyexasol_mock_base import (
    MockConnection,
    connect_with_handlers,
    normalize_query,
    result_statement,
)

from exasol.ansible_modules.exasol_info import (
    CLUSTER_SIZE_QUERY,
    DATABASE_NAME_QUERY,
    VERSION_QUERY,
)


def connect(**kwargs: Any) -> MockConnection:
    """Return an exasol_info-specific mock Exasol connection."""
    return connect_with_handlers(
        connect_kwargs=kwargs,
        statement_handlers=STATEMENT_HANDLERS,
    )


def query_key(query: str) -> str:
    """Normalize a query the same way the mock connection matches it."""
    return normalize_query(query).upper()


STATEMENT_HANDLERS = {
    query_key(VERSION_QUERY): lambda _connection, _query, _params: (
        result_statement(rows=[{"VERSION": "8.39.1"}])
    ),
    query_key(DATABASE_NAME_QUERY): lambda _connection, _query, _params: (
        result_statement(rows=[{"DATABASE_NAME": "EXA_DB"}])
    ),
    query_key(CLUSTER_SIZE_QUERY): lambda _connection, _query, _params: (
        result_statement(rows=[{"CLUSTER_SIZE": 1}])
    ),
}
