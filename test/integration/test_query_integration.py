"""Pure Python backend integration tests for the query runtime."""

from __future__ import annotations

import pytest
from test.integration.integration_common import (
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
    result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": (
                "SELECT PARAM_VALUE FROM EXA_METADATA "
                "WHERE PARAM_NAME = 'databaseProductVersion'"
            ),
        }
    )

    assert result["changed"] is False
    assert result["query_result"]
    assert result["query_result"][0]["PARAM_VALUE"]


@pytest.mark.integration
@pytest.mark.slow
def test_query_runtime_check_mode_predicts_write_without_executing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify query check mode reports writes without changing backend state."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    query = f'CREATE SCHEMA "{schema_name}"'

    predicted_result = exasol_query.check_mode_result(
        exasol_query.normalize_query_list(query)
    )
    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )

    assert predicted_result == {
        "changed": True,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": [query],
        "rowcount": [],
        "execution_time_ms": [],
    }
    assert schema_count == 0


@pytest.mark.integration
@pytest.mark.slow
def test_query_runtime_check_mode_ignores_read_only_query(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify query check mode keeps read-only statements on the execution path."""
    query = (
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion'"
    )

    predicted_result = exasol_query.check_mode_result(
        exasol_query.normalize_query_list(query)
    )
    executed_result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": query,
        }
    )

    assert predicted_result is None
    assert executed_result["changed"] is False
    assert executed_result["query_result"]
