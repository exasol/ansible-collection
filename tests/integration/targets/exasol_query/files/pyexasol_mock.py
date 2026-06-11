"""exasol_query-specific pyexasol mock scenarios."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
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
    "SELECT MOCK_JSON_VALUES": lambda _connection, _query, _params: (
        json_values_statement()
    ),
    "SELECT MOCK_TUPLE_ROW": lambda _connection, _query, _params: tuple_row_statement(),
    "SELECT {__POS_0!D} AS A": lambda _connection, _query, params: (
        result_statement(rows=[{"A": params["__pos_0"]}])
    ),
    "SELECT {N!D} AS A": lambda _connection, _query, params: (
        result_statement(rows=[{"A": params["n"]}])
    ),
    "SELECT {__POS_0!D} AS A, {N!D} AS B, '?' AS LITERAL, TRUE::BOOLEAN AS FLAG": (
        lambda _connection, _query, params: bound_args_statement(params)
    ),
    "SELECT 1 AS A": lambda _connection, _query, _params: (
        result_statement(rows=[{"A": 1}])
    ),
}

QUERY_ERRORS = {
    "MOCK_RAISE_SECRET": "query failed with password swordfish and token token-value",
}


def connect(**kwargs: Any) -> "MockConnection":
    """Return an exasol_query-specific mock Exasol connection."""
    return connect_with_handlers(
        connect_kwargs=kwargs,
        statement_handlers=STATEMENT_HANDLERS,
        query_errors=QUERY_ERRORS,
    )


def connection_kwargs_statement(connection: MockConnection) -> MockStatement:
    return result_statement(
        rows=[
            {
                "KWARGS": public_connect_kwargs(connection.connect_kwargs),
                "PASSWORD_IS_SET": connection.connect_kwargs.get("password")
                is not None,
            }
        ],
    )


def json_values_statement() -> MockStatement:
    return result_statement(
        rows=[
            {
                "AMOUNT": Decimal("1.5"),
                "CREATED_ON": dt.date(2026, 1, 2),
                "PAYLOAD": b"\x01\x02",
            }
        ],
    )


def tuple_row_statement() -> MockStatement:
    return result_statement(
        rows=[(42, "answer")],
        column_names=["A", "NOTE"],
    )


def bound_args_statement(params: dict[str, Any]) -> MockStatement:
    return result_statement(
        rows=[
            {
                "A": params["__pos_0"],
                "B": params["n"],
                "LITERAL": "?",
                "FLAG": "true::boolean",
            }
        ],
    )
