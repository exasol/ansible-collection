"""Shared Exasol catalog-count assertions for integration tests."""

from __future__ import annotations

from ansible_playbook.common_helpers import connect_to_exasol


def catalog_count(
    login_vars: dict[str, object],
    *,
    table: str,
    column: str,
    object_name: str,
    result_key: str,
) -> int:
    """Read one catalog object count through a plain Exasol connection."""
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(
            f"SELECT COUNT(*) AS {result_key} "
            f"FROM {table} WHERE {column} = '{object_name}'"
        ).fetchall()
    finally:
        connection.close()

    return _row_int(rows[0], result_key)


def _row_int(row: object, key: str) -> int:
    if isinstance(row, dict):
        return int(row[key])

    return int(row[0])
