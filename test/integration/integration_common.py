"""Shared helpers for Python-package integration tests."""

from __future__ import annotations

import uuid
from typing import Any

from exasol.ansible_modules import exasol_query


def unique_name(prefix: str) -> str:
    """Return a unique Exasol object name for one integration test."""
    return f"{prefix}_{uuid.uuid4().hex.upper()}"


def row_int(row: object, key: str) -> int:
    """Read one integer field from a dict or tuple-like row."""
    value: Any
    if isinstance(row, dict):
        value = row[key]
    else:
        value = row[0]
    return int(value)


def catalog_count(
    login_vars: dict[str, object],
    *,
    table: str,
    column: str,
    object_name: str,
    result_key: str,
) -> int:
    """Read one catalog object count through a plain Exasol connection."""
    with exasol_query.connect_to_exasol(
        login_vars,
        module_name="python package integration test",
    ) as connection:
        rows = connection.execute(
            f"SELECT COUNT(*) AS {result_key} "
            f"FROM {table} WHERE {column} = '{object_name}'"
        ).fetchall()

    return row_int(rows[0], result_key)


def execute_sql(login_vars: dict[str, object], query: str) -> None:
    """Execute one SQL statement through a plain Exasol connection."""
    with exasol_query.connect_to_exasol(
        login_vars,
        module_name="python package integration test",
    ) as connection:
        connection.execute(query)
