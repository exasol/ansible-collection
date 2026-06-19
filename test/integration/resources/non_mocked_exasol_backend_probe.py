"""Probe script copied into an Ansible runner workspace by integration tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pyexasol

from exasol.ansible_modules.exasol_query import (
    build_exasol_connect_kwargs,
    to_json_safe,
)
from exasol.ansible_modules.exasol_user import quote_identifier

CONNECTION_PARAMETER_NAMES = (
    "login_host",
    "login_port",
    "login_user",
    "login_password",
    "login_schema",
    "autocommit",
    "compression",
    "validate_certs",
    "client_kwargs",
    "fetch_size",
    "ca_cert",
    "certificate_fingerprint",
)


def main(params_file: str) -> None:
    """Execute a small probe against a non-mocked Exasol backend."""
    params = json.loads(Path(params_file).read_text())
    schema_name = params["test_schema"]
    quoted_schema = quote_identifier(schema_name)
    quoted_table = f'{quoted_schema}."RUNNER_BACKEND_CHECK"'
    connection = pyexasol.connect(
        **build_exasol_connect_kwargs(_connection_parameters(params)),
    )
    try:
        connection.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
        connection.execute(
            f"CREATE OR REPLACE TABLE {quoted_table} "
            "(ID DECIMAL(18, 0), NOTE VARCHAR(200))"
        )
        connection.execute(f"INSERT INTO {quoted_table} VALUES (1, 'runner-wrapper')")
        summary_query = (
            f"SELECT COUNT(*) AS ROW_COUNT, MIN(NOTE) AS NOTE FROM {quoted_table}"
        )
        row = connection.execute(summary_query).fetchone()
        selected_row = connection.execute("SELECT 42 AS SELECTED_VALUE").fetchone()
        print(
            json.dumps(
                to_json_safe(
                    {
                        "schema": schema_name,
                        "row_count": int(_row_value(row, "ROW_COUNT", 0)),
                        "note": _row_value(row, "NOTE", 1),
                        "selected_value": int(
                            _row_value(
                                selected_row,
                                "SELECTED_VALUE",
                                0,
                            )
                        ),
                    }
                )
            )
        )
    finally:
        try:
            connection.execute(f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE")
        finally:
            connection.close()


def _connection_parameters(params: dict[str, Any]) -> dict[str, Any]:
    return {name: params[name] for name in CONNECTION_PARAMETER_NAMES if name in params}


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row[key]

    return row[index]


if __name__ == "__main__":
    main(sys.argv[1])
