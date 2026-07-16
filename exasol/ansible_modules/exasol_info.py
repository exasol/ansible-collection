"""Runtime helpers for read-only Exasol server information gathering."""

from __future__ import annotations

from collections.abc import Mapping
from typing import (
    Any,
    cast,
)

from exasol.ansible_modules import common_query

VERSION_QUERY = """
                SELECT PARAM_VALUE AS VERSION
                FROM SYS.EXA_METADATA
                WHERE PARAM_NAME = 'databaseProductVersion' \
                """
DATABASE_NAME_QUERY = """
                      SELECT PARAM_VALUE AS DATABASE_NAME
                      FROM SYS.EXA_METADATA
                      WHERE PARAM_NAME = 'databaseName' \
                      """
CLUSTER_SIZE_QUERY = "SELECT NODES AS CLUSTER_SIZE FROM EXA_SYSTEM_EVENTS"

exasol_connection_argument_spec = common_query.exasol_connection_argument_spec
connect_to_exasol = common_query.connect_to_exasol
sanitize_error_message = common_query.sanitize_error_message
normalized_exasol_error_message = common_query.normalized_exasol_error_message


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the info module."""
    return {
        **common_query.exasol_connection_argument_spec(),
    }


def run_info(params: Mapping[str, Any]) -> dict[str, object]:
    """Connect to Exasol and gather the requested server information."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_info",
    ) as connection:
        version = _query_version(connection)
        database_name = _query_database_name(connection)
        cluster_size = _query_cluster_size(connection)

        return {
            "changed": False,
            "version": version,
            "database_name": database_name,
            "cluster_size": cluster_size,
        }


def _query_cluster_size(connection: object) -> int:
    result = common_query.execute_queries(connection, CLUSTER_SIZE_QUERY)
    rows = result["query_result"]
    row = cast(Mapping[str, Any], rows[0])
    return cast(int, row["CLUSTER_SIZE"])


def _query_version(connection: object) -> str:
    result = common_query.execute_queries(connection, VERSION_QUERY)
    rows = result["query_result"]
    return cast(str, cast(Mapping[str, Any], rows[0])["VERSION"])


def _query_database_name(connection: object) -> str:
    result = common_query.execute_queries(connection, DATABASE_NAME_QUERY)
    rows = result["query_result"]
    row = cast(Mapping[str, Any], rows[0])
    return cast(str, row["DATABASE_NAME"])
