"""Playbook-backed tests for exasol-query feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    connect_to_exasol,
    given_acceptance_context,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)

from exasol.ansible_modules.common_identifier_validation import quote_identifier

MODULE_NAME = "exasol_query"


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_read_metadata_version(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Read database version metadata."""
    scenario_id = "exasol-query-read-metadata-version"
    playbook = """
    - name: Read database version metadata
      block:
        - name: When exasol_query runs a read-only EXA_METADATA query
          exasol.exasol.exasol_query:
            query: >-
              SELECT PARAM_VALUE
              FROM EXA_METADATA
              WHERE PARAM_NAME = 'databaseProductVersion'
          register: exasol_query_metadata_version

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_metadata_version }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]
    expected_query = (
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion'"
    )

    assert len(module_result["query_result"]) == 1
    assert module_result["query_result"][0]["PARAM_VALUE"]
    _assert_query_module_result(
        module_result,
        changed=False,
        query_result=module_result["query_result"],
        query_all_results=[module_result["query_result"]],
        executed_queries=[expected_query],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_single_select(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Execute single SELECT."""
    scenario_id = "exasol-query-single-select"
    playbook = """
    - name: Execute single SELECT
      block:
        - name: When exasol_query runs a single SELECT
          exasol.exasol.exasol_query:
            query: SELECT 11 AS A
          register: exasol_query_select

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_select }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    _assert_query_module_result(
        module_result,
        changed=False,
        query_result=[{"A": 11}],
        query_all_results=[[{"A": 11}]],
        executed_queries=["SELECT 11 AS A"],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_batch_statements(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Execute statement batch on one connection."""
    scenario_id = "exasol-query-batch-statements"
    playbook = """
    - name: Execute statement batch on one connection
      block:
        - name: When exasol_query runs a list of statements
          exasol.exasol.exasol_query:
            query:
              - CREATE SCHEMA {{ test_schema }}
              - CREATE OR REPLACE TABLE {{ test_schema }}.QUERY_TEST
                (ID DECIMAL(18, 0), NOTE VARCHAR(200))
              - INSERT INTO {{ test_schema }}.QUERY_TEST VALUES (1, 'backend')
              - INSERT INTO {{ test_schema }}.QUERY_TEST VALUES (2, 'backend')
              - SELECT COUNT(*) AS ROW_COUNT, MIN(NOTE) AS NOTE
                FROM {{ test_schema }}.QUERY_TEST
          register: exasol_query_batch

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_batch }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]
    expected_queries = [
        f"CREATE SCHEMA {context.test_schema}",
        (
            f"CREATE OR REPLACE TABLE {context.test_schema}.QUERY_TEST "
            "(ID DECIMAL(18, 0), NOTE VARCHAR(200))"
        ),
        f"INSERT INTO {context.test_schema}.QUERY_TEST VALUES (1, 'backend')",
        f"INSERT INTO {context.test_schema}.QUERY_TEST VALUES (2, 'backend')",
        (
            "SELECT COUNT(*) AS ROW_COUNT, MIN(NOTE) AS NOTE "
            f"FROM {context.test_schema}.QUERY_TEST"
        ),
    ]

    _assert_query_module_result(
        module_result,
        changed=True,
        query_result=[{"ROW_COUNT": 2, "NOTE": "backend"}],
        query_all_results=[
            [],
            [],
            [],
            [],
            [{"ROW_COUNT": 2, "NOTE": "backend"}],
        ],
        executed_queries=expected_queries,
    )

    # Verify the batch side effect directly
    quoted_table = f'{quote_identifier(context.test_schema)}."QUERY_TEST"'
    connection = connect_to_exasol(context.login_vars)
    try:
        rows = connection.execute(
            f"SELECT ID, NOTE FROM {quoted_table} ORDER BY ID"
        ).fetchall()
    finally:
        connection.close()

    assert [
        (str(_row_value(row, "ID", 0)), _row_value(row, "NOTE", 1)) for row in rows
    ] == [
        ("1", "backend"),
        ("2", "backend"),
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_positional_args(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Bind positional arguments."""
    scenario_id = "exasol-query-positional-args"
    playbook = """
    - name: Bind positional arguments
      block:
        - name: When exasol_query runs with positional args
          exasol.exasol.exasol_query:
            query: SELECT ? AS A
            positional_args:
              - 42
          register: exasol_query_positional

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_positional }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    _assert_query_module_result(
        module_result,
        changed=False,
        query_result=[{"A": 42}],
        query_all_results=[[{"A": 42}]],
        executed_queries=["SELECT ? AS A"],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_named_args(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Bind named arguments."""
    scenario_id = "exasol-query-named-args"
    playbook = """
    - name: Bind named arguments
      block:
        - name: When exasol_query runs with named args
          exasol.exasol.exasol_query:
            query: SELECT :n AS A
            named_args:
              n: 7
          register: exasol_query_named

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_named }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    _assert_query_module_result(
        module_result,
        changed=False,
        query_result=[{"A": 7}],
        query_all_results=[[{"A": 7}]],
        executed_queries=["SELECT :n AS A"],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_check_mode_select(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Execute read-only query in check mode."""
    scenario_id = "exasol-query-check-mode-select"
    playbook = """
    - name: Execute read-only query in check mode
      block:
        - name: When exasol_query runs a SELECT in check mode
          exasol.exasol.exasol_query:
            query: SELECT 13 AS A
          check_mode: true
          register: exasol_query_check_mode_select

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_check_mode_select }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    _assert_query_module_result(
        module_result,
        changed=False,
        query_result=[{"A": 13}],
        query_all_results=[[{"A": 13}]],
        executed_queries=["SELECT 13 AS A"],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_check_mode_write(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Predict write in check mode without execution."""
    scenario_id = "exasol-query-check-mode-write"
    playbook = """
    - name: Predict write in check mode without execution
      block:
        - name: When exasol_query predicts DDL in check mode
          exasol.exasol.exasol_query:
            query: CREATE SCHEMA {{ test_schema }}_CHECK_MODE
          check_mode: true
          register: exasol_query_check_mode_ddl

        - name: Read check-mode schema metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS SCHEMA_COUNT
              FROM EXA_SCHEMAS
              WHERE SCHEMA_NAME = '{{ test_schema }}_CHECK_MODE'
          register: exasol_query_check_mode_schema

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              predicted_result: "{{ exasol_query_check_mode_ddl }}"
              schema_check_result: "{{ exasol_query_check_mode_schema }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    predicted_result = result["predicted_result"]
    schema_check_result = result["schema_check_result"]

    assert predicted_result == {
        "changed": True,
        "failed": False,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": [f"CREATE SCHEMA {context.test_schema}_CHECK_MODE"],
        "rowcount": [],
        "execution_time_ms": [],
    }
    _assert_query_module_result(
        schema_check_result,
        changed=False,
        query_result=[{"SCHEMA_COUNT": 0}],
        query_all_results=[[{"SCHEMA_COUNT": 0}]],
        executed_queries=[
            (
                "SELECT COUNT(*) AS SCHEMA_COUNT FROM EXA_SCHEMAS "
                f"WHERE SCHEMA_NAME = '{context.test_schema}_CHECK_MODE'"
            )
        ],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_sanitize_bad_credentials(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Sanitize bad credential errors."""
    scenario_id = "exasol-query-sanitize-bad-credentials"
    playbook = """
    - name: Sanitize bad credential errors
      block:
        - name: When exasol_query runs with bad credentials
          exasol.exasol.exasol_query:
            login_host: "{{ login_host }}"
            login_port: "{{ login_port }}"
            login_user: "{{ login_user }}"
            login_password: "{{ invalid_login_password }}"
            validate_certs: "{{ validate_certs }}"
            certificate_fingerprint: "{{ certificate_fingerprint | default('') }}"
            query: SELECT 1 AS A
          register: exasol_query_bad_credentials
          ignore_errors: true

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_query_bad_credentials }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    assert module_result["failed"] is True
    assert "authenticate" in module_result["msg"]
    then_secret_is_not_exposed(result, context.invalid_login_password)


def _without_dynamic_metadata(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key not in {"rowcount", "execution_time_ms"}
    }


def _assert_query_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    query_result: list[dict[str, object]],
    query_all_results: list[list[dict[str, object]]],
    executed_queries: list[str],
) -> None:
    assert _without_dynamic_metadata(result) == {
        "changed": changed,
        "failed": False,
        "query_result": query_result,
        "query_all_results": query_all_results,
        "executed_queries": executed_queries,
    }
    _assert_rowcount_count(result, len(executed_queries))
    _assert_execution_time_ms(result, expected_count=len(executed_queries))


def _assert_rowcount_count(result: dict[str, Any], expected: int) -> None:
    assert len(result["rowcount"]) == expected


def _assert_execution_time_ms(result: dict[str, Any], expected_count: int) -> None:
    execution_time_ms = result["execution_time_ms"]

    assert len(execution_time_ms) == expected_count
    assert all(isinstance(value, (int, float)) for value in execution_time_ms)
    assert all(value >= 0 for value in execution_time_ms)


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[key]

    return row[index]
