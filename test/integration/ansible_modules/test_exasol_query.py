"""Pure Python backend integration tests for the query runtime."""

from __future__ import annotations

import pytest
from ansible_modules.common_helpers import unique_name
from common.catalog_assertions import catalog_count

from exasol.ansible_modules import exasol_query


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-query-execute-write-query-against-backend")
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
@pytest.mark.scenario_id("exasol-query-execute-read-query-against-backend")
def test_query_runtime_executes_read_query_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the query runtime can execute read-only SQL through its run helper."""
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
@pytest.mark.scenario_id("exasol-query-check-mode-ignores-read-only-query")
def test_query_runtime_check_mode_ignores_read_only_query(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify query check mode keeps read-only statements on the execution path."""
    query = (
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion'"
    )
    queries = exasol_query.normalize_query_list(query)

    predicted_result = exasol_query.check_mode_result(queries)
    executed_result = exasol_query.run_query(
        {
            **exasol_login_vars,
            "query": query,
        }
    )

    assert predicted_result is None
    assert executed_result["changed"] is False
    assert executed_result["query_result"]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-query-check-mode-predicts-write-without-execution")
def test_query_runtime_check_mode_predicts_write_without_execution(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify query check mode predicts write SQL without executing it."""
    schema_name = unique_name("ANSIBLE_PYTHON_CHECK_MODE_SCHEMA")
    query = f'CREATE SCHEMA "{schema_name}"'
    queries = exasol_query.normalize_query_list(query)

    predicted_result = exasol_query.check_mode_result(queries)
    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )

    assert predicted_result is not None
    assert predicted_result["changed"] is True
    assert predicted_result["executed_queries"] == [query]
    assert predicted_result["query_result"] == []
    assert schema_count == 0


@pytest.mark.scenario_id(
    "exasol-query-check-mode-predicts-no-action-for-comment-only-query"
)
def test_query_runtime_check_mode_predicts_no_action_for_comment_only_query() -> None:
    """Verify check mode predicts no action for a query with no real statement.

    Regression test: a comment-only (or otherwise statement-less) query has no
    real SQL to execute, matching pyexasol's own script splitter, which
    discards such content rather than treating it as a pending write.
    """
    query = "-- nothing to do"
    queries = exasol_query.normalize_query_list(query)

    predicted_result = exasol_query.check_mode_result(queries)

    assert predicted_result is None
