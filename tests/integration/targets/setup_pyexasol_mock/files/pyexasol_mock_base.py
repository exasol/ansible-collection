"""Reusable pyexasol test double support for Ansible integration targets."""

from __future__ import annotations

import copy
from collections.abc import (
    Callable,
    Mapping,
)
from typing import Any

StatementHandler = Callable[["MockConnection", str, dict[str, Any]], "MockStatement"]


def connect_with_handlers(
    connect_kwargs: dict[str, Any],
    statement_handlers: Mapping[str, StatementHandler],
    authentication_errors: Mapping[str, str] | None = None,
    query_errors: Mapping[str, str] | None = None,
) -> MockConnection:
    """Return a mock Exasol connection configured with statement handlers."""
    authentication_errors = authentication_errors or {}
    password = connect_kwargs.get("password")
    if isinstance(password, str) and password in authentication_errors:
        raise RuntimeError(authentication_errors[password])

    return MockConnection(
        connect_kwargs=connect_kwargs,
        statement_handlers=statement_handlers,
        query_errors=query_errors or {},
    )


class MockConnection:
    """Small pyexasol connection test double."""

    def __init__(
        self,
        connect_kwargs: dict[str, Any],
        statement_handlers: Mapping[str, StatementHandler],
        query_errors: Mapping[str, str],
    ) -> None:
        self.connect_kwargs = connect_kwargs
        self.statement_handlers = statement_handlers
        self.query_errors = query_errors
        self.execution_count = 0
        self.closed = False

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> MockStatement:
        """Execute a mock SQL statement."""
        self.execution_count += 1
        normalized_query = normalize_query(query)
        upper_query = normalized_query.upper()
        params = query_params or {}

        for marker, message in self.query_errors.items():
            if marker in upper_query:
                raise RuntimeError(message)

        if upper_query in self.statement_handlers:
            return self.statement_handlers[upper_query](self, upper_query, params)

        if is_rowcount_statement(upper_query):
            return rowcount_statement()

        raise RuntimeError(f"unexpected mock query: {query}")

    def close(self) -> None:
        """Close the mock connection."""
        self.closed = True


class MockStatement:
    """Small pyexasol statement test double."""

    def __init__(
        self,
        rows: list[Any],
        result_type: str = "resultSet",
        rowcount: int = 0,
        execution_time: float = 0.001,
        column_names: list[str] | None = None,
    ) -> None:
        self._rows = rows
        self.result_type = result_type
        self._rowcount = rowcount
        self.execution_time = execution_time
        self.col_names = column_names or []

    def fetchall(self) -> list[Any]:
        """Return mock result rows."""
        return self._rows

    def rowcount(self) -> int:
        """Return mock row count."""
        return self._rowcount

    def column_names(self) -> list[str]:
        """Return mock column names."""
        return self.col_names


def result_statement(
    rows: list[Any],
    rowcount: int = 1,
    column_names: list[str] | None = None,
) -> MockStatement:
    """Return a result-set statement with common defaults."""
    return MockStatement(
        rows=rows,
        rowcount=rowcount,
        column_names=column_names,
    )


def rowcount_statement(
    rowcount: int = 0,
    execution_time: float = 0.002,
) -> MockStatement:
    """Return a row-count statement with common defaults."""
    return MockStatement(
        rows=[],
        result_type="rowCount",
        rowcount=rowcount,
        execution_time=execution_time,
    )


def public_connect_kwargs(connect_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return connect kwargs safe to expose in module results."""
    public_kwargs = copy.deepcopy(connect_kwargs)
    public_kwargs.pop("access_token", None)
    public_kwargs.pop("password", None)
    public_kwargs.pop("refresh_token", None)
    return public_kwargs


def normalize_query(query: str) -> str:
    """Normalize SQL text for straightforward mock statement matching."""
    return " ".join(query.strip().split())


def is_rowcount_statement(query: str) -> bool:
    """Return whether a query should behave like DDL or DML."""
    return query.split(" ", 1)[0] in {
        "ALTER",
        "CREATE",
        "DELETE",
        "DROP",
        "INSERT",
        "MERGE",
        "TRUNCATE",
        "UPDATE",
    }
