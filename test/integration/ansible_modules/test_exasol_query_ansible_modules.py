"""Pure Python backend integration tests for the query runtime."""

from __future__ import annotations

import pytest
from integration_common import (
    catalog_count,
    unique_name,
)

from exasol.ansible_modules import exasol_query


@pytest.mark.integration
@pytest.mark.slow
def test_query_runtime_executes_write_query_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the query runtime can execute write SQL through its run helper."""
    scenario_id = "exasol-query-execute-write-query-against-backend"
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    create_result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": f'CREATE SCHEMA "{schema_name}"',
        }
    )
    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )

    assert create_result["changed"] is True
    assert create_result["executed_queries"] == [f'CREATE SCHEMA "{schema_name}"']
    assert schema_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_query_runtime_executes_read_query_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the query runtime can execute read-only SQL through its run helper."""
    scenario_id = "exasol-query-execute-read-query-against-backend"
    query = "SELECT 1 AS TEST_VALUE"

    result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": query,
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == [query]
    assert result["query_result"] == [{"TEST_VALUE": 1}]


@pytest.mark.integration
@pytest.mark.slow
def test_query_runtime_check_mode_ignores_read_only_query(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify query check mode keeps read-only statements on the execution path."""
    scenario_id = "exasol-query-check-mode-ignores-read-only-query"
    query = (
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion'"
    )
    executed_result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": query,
        }
    )

    assert executed_result["changed"] is False
    assert executed_result["query_result"]
