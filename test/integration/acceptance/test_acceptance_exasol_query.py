"""Playbook-backed tests for exasol-query feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    given_acceptance_context,
    then_result_matches,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)

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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: When exasol_query runs a read-only EXA_METADATA query
          exasol.exasol.exasol_query:
            query: >-
              SELECT PARAM_VALUE
              FROM EXA_METADATA
              WHERE PARAM_NAME = 'databaseProductVersion'
          register: exasol_query_metadata_version

        - name: Then database version metadata is returned without changes
          ansible.builtin.assert:
            that:
              - exasol_query_metadata_version is not changed
              - exasol_query_metadata_version.query_result | length == 1
              - >-
                exasol_query_metadata_version.query_result[0].PARAM_VALUE
                | string | length > 0
              - exasol_query_metadata_version.execution_time_ms | length == 1

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: false
              metadata_version_available: true
              result_count: "{{ exasol_query_metadata_version.query_result | length }}"
              execution_time_count: >-
                {{ exasol_query_metadata_version.execution_time_ms | length }}
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "metadata_version_available": True,
            "result_count": "1",
            "execution_time_count": "1",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: When exasol_query runs a single SELECT
          exasol.exasol.exasol_query:
            query: SELECT 11 AS A
          register: exasol_query_select

        - name: Then the SELECT returns rows and does not change
          ansible.builtin.assert:
            that:
              - exasol_query_select is not changed
              - exasol_query_select.query_result | length == 1
              - exasol_query_select.query_result[0].A | string == "11"
              - exasol_query_select.query_all_results | length == 1
              - exasol_query_select.executed_queries == ["SELECT 11 AS A"]
              - exasol_query_select.rowcount | length == 1
              - exasol_query_select.execution_time_ms | length == 1

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: false
              value: "{{ exasol_query_select.query_result[0].A | string }}"
              all_result_count: "{{ exasol_query_select.query_all_results | length }}"
              executed_queries:
                - SELECT 11 AS A
              rowcount_count: "{{ exasol_query_select.rowcount | length }}"
              execution_time_count: >-
                {{ exasol_query_select.execution_time_ms | length }}
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "value": "11",
            "all_result_count": "1",
            "executed_queries": ["SELECT 11 AS A"],
            "rowcount_count": "1",
            "execution_time_count": "1",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: Given the disposable schema does not exist
          exasol.exasol.exasol_query:
            query: DROP SCHEMA IF EXISTS {{ test_schema }} CASCADE

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

        - name: Then statement order and result shape are preserved
          ansible.builtin.assert:
            that:
              - exasol_query_batch is changed
              - exasol_query_batch.executed_queries == expected_batch_queries
              - >-
                exasol_query_batch.query_all_results | length
                == expected_batch_queries | length
              - >-
                exasol_query_batch.rowcount | length
                == expected_batch_queries | length
              - >-
                exasol_query_batch.execution_time_ms | length
                == expected_batch_queries | length
              - exasol_query_batch.query_result | length == 1
              - exasol_query_batch.query_result[0].ROW_COUNT | string == "2"
              - exasol_query_batch.query_result[0].NOTE == "backend"
          vars:
            expected_batch_queries:
              - CREATE SCHEMA {{ test_schema }}
              - CREATE OR REPLACE TABLE {{ test_schema }}.QUERY_TEST
                (ID DECIMAL(18, 0), NOTE VARCHAR(200))
              - INSERT INTO {{ test_schema }}.QUERY_TEST VALUES (1, 'backend')
              - INSERT INTO {{ test_schema }}.QUERY_TEST VALUES (2, 'backend')
              - SELECT COUNT(*) AS ROW_COUNT, MIN(NOTE) AS NOTE
                FROM {{ test_schema }}.QUERY_TEST

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: true
              schema: "{{ test_schema }}"
              query_count: "{{ exasol_query_batch.executed_queries | length }}"
              all_result_count: "{{ exasol_query_batch.query_all_results | length }}"
              rowcount_count: "{{ exasol_query_batch.rowcount | length }}"
              execution_time_count: >-
                {{ exasol_query_batch.execution_time_ms | length }}
              row_count: "{{ exasol_query_batch.query_result[0].ROW_COUNT | string }}"
              note: "{{ exasol_query_batch.query_result[0].NOTE }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": True,
            "schema": context.test_schema,
            "query_count": "5",
            "all_result_count": "5",
            "rowcount_count": "5",
            "execution_time_count": "5",
            "row_count": "2",
            "note": "backend",
        },
    )


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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: When exasol_query runs with positional args
          exasol.exasol.exasol_query:
            query: SELECT ? AS A
            positional_args:
              - 42
          register: exasol_query_positional

        - name: Then positional args are bound correctly
          ansible.builtin.assert:
            that:
              - exasol_query_positional is not changed
              - exasol_query_positional.query_result[0].A | string == "42"

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: false
              value: "{{ exasol_query_positional.query_result[0].A | string }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "value": "42",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: When exasol_query runs with named args
          exasol.exasol.exasol_query:
            query: SELECT :n AS A
            named_args:
              n: 7
          register: exasol_query_named

        - name: Then named args are bound correctly
          ansible.builtin.assert:
            that:
              - exasol_query_named is not changed
              - exasol_query_named.query_result[0].A | string == "7"

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: false
              value: "{{ exasol_query_named.query_result[0].A | string }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "value": "7",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: When exasol_query runs a SELECT in check mode
          exasol.exasol.exasol_query:
            query: SELECT 13 AS A
          check_mode: true
          register: exasol_query_check_mode_select

        - name: Then the SELECT succeeds without change
          ansible.builtin.assert:
            that:
              - exasol_query_check_mode_select is not changed
              - exasol_query_check_mode_select.query_result | length == 1
              - exasol_query_check_mode_select.query_result[0].A | string == "13"

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: false
              value: >-
                {{ exasol_query_check_mode_select.query_result[0].A | string }}
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "value": "13",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
      block:
        - name: Given the check-mode schema does not exist
          exasol.exasol.exasol_query:
            query: DROP SCHEMA IF EXISTS {{ test_schema }}_CHECK_MODE CASCADE

        - name: When exasol_query predicts DDL in check mode
          exasol.exasol.exasol_query:
            query: CREATE SCHEMA {{ test_schema }}_CHECK_MODE
          check_mode: true
          register: exasol_query_check_mode_ddl

        - name: Then the module reports the predicted change
          ansible.builtin.assert:
            that:
              - exasol_query_check_mode_ddl is changed
              - exasol_query_check_mode_ddl.query_result == []
              - exasol_query_check_mode_ddl.query_all_results == []
              - exasol_query_check_mode_ddl.rowcount == []
              - exasol_query_check_mode_ddl.execution_time_ms == []

        - name: Then the check-mode schema was not created
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS SCHEMA_COUNT
              FROM EXA_SCHEMAS
              WHERE SCHEMA_NAME = '{{ test_schema }}_CHECK_MODE'
          register: exasol_query_check_mode_schema

        - name: Assert check mode DDL was not executed
          ansible.builtin.assert:
            that:
              - >-
                exasol_query_check_mode_schema.query_result[0].SCHEMA_COUNT
                | string == "0"

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              changed: true
              query_result: []
              query_all_results: []
              rowcount: []
              execution_time_ms: []
              schema_count: >-
                {{ exasol_query_check_mode_schema.query_result[0].SCHEMA_COUNT
                | string }}
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        result,
        {
            "changed": True,
            "query_result": [],
            "query_all_results": [],
            "rowcount": [],
            "execution_time_ms": [],
            "schema_count": "0",
        },
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
      vars:
        acceptance_current_scenario_id: "{{ acceptance_scenario_id }}"
      when: >-
        (acceptance_scenario_id | default(''))
        in ['', acceptance_current_scenario_id]
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

        - name: Then bad credential errors are sanitized
          ansible.builtin.assert:
            that:
              - exasol_query_bad_credentials is failed
              - "'authenticate' in exasol_query_bad_credentials.msg"
              - invalid_login_password not in exasol_query_bad_credentials.msg

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_current_scenario_id }}"
              failed: true
              authentication_error: true
              result_json: "{{ exasol_query_bad_credentials | to_json }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    then_result_matches(
        _without_result_json(result),
        {
            "failed": True,
            "authentication_error": True,
        },
    )
    then_secret_is_not_exposed(result, context.invalid_login_password)


def _without_result_json(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "result_json"}
