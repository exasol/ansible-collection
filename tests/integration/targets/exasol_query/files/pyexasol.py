"""Mock pyexasol module for exasol_query Ansible integration tests."""

from __future__ import annotations

import copy
import datetime as dt
from decimal import Decimal
from typing import Any


def connect(**kwargs: Any) -> "MockConnection":
    """Return a mock Exasol connection."""
    if kwargs.get("password") == "bad-secret":
        raise RuntimeError("authentication failed for password bad-secret")

    return MockConnection(kwargs)


class MockConnection:
    """Small pyexasol connection test double."""

    def __init__(self, connect_kwargs: dict[str, Any]) -> None:
        self.connect_kwargs = connect_kwargs
        self.execution_count = 0
        self.closed = False

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> "MockStatement":
        """Execute a mock SQL statement."""
        self.execution_count += 1
        normalized_query = " ".join(query.strip().split())
        upper_query = normalized_query.upper()
        params = query_params or {}

        if "MOCK_RAISE_SECRET" in upper_query:
            raise RuntimeError(
                "query failed with password swordfish and token token-value"
            )

        if upper_query == "SELECT MOCK_CONNECTION_KWARGS":
            return MockStatement(
                rows=[
                    {
                        "KWARGS": public_connect_kwargs(self.connect_kwargs),
                        "PASSWORD_IS_SET": self.connect_kwargs.get("password")
                        is not None,
                    }
                ],
                rowcount=1,
            )

        if upper_query == "SELECT MOCK_JSON_VALUES":
            return MockStatement(
                rows=[
                    {
                        "AMOUNT": Decimal("1.5"),
                        "CREATED_ON": dt.date(2026, 1, 2),
                        "PAYLOAD": b"\x01\x02",
                    }
                ],
                rowcount=1,
            )

        if upper_query == "SELECT MOCK_TUPLE_ROW":
            return MockStatement(
                rows=[(42, "answer")],
                rowcount=1,
                column_names=["A", "NOTE"],
            )

        if upper_query == "SELECT {__POS_0!D} AS A":
            return MockStatement(rows=[{"A": params["__pos_0"]}], rowcount=1)

        if upper_query == "SELECT {N!D} AS A":
            return MockStatement(rows=[{"A": params["n"]}], rowcount=1)

        if (
            upper_query
            == "SELECT {__POS_0!D} AS A, {N!D} AS B, '?' AS LITERAL, TRUE::BOOLEAN AS FLAG"
        ):
            return MockStatement(
                rows=[
                    {
                        "A": params["__pos_0"],
                        "B": params["n"],
                        "LITERAL": "?",
                        "FLAG": "true::boolean",
                    }
                ],
                rowcount=1,
            )

        if upper_query == "SELECT 1 AS A":
            return MockStatement(rows=[{"A": 1}], rowcount=1)

        if is_rowcount_statement(upper_query):
            return MockStatement(
                rows=[],
                result_type="rowCount",
                rowcount=0,
                execution_time=0.002,
            )

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


def public_connect_kwargs(connect_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return connect kwargs safe to expose in module results."""
    public_kwargs = copy.deepcopy(connect_kwargs)
    public_kwargs.pop("password", None)
    return public_kwargs


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
