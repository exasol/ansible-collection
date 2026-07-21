"""Playbook-backed tests for exasol-script feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from ansible_playbook.common_helpers import (
    connect_to_exasol,
    given_acceptance_context,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)

MODULE_NAME = "exasol_script"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-simple-multi-statement-script")
def test_exasol_script_execute_simple_multi_statement_script(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Execute simple multi-statement script
      block:
        - name: When exasol_script runs a script creating a schema, a table, and a row
          exasol.exasol.exasol_script:
            script: |
              CREATE SCHEMA {{ test_schema }};
              CREATE TABLE {{ test_schema }}.SCRIPT_TEST (ID DECIMAL(18, 0));
              INSERT INTO {{ test_schema }}.SCRIPT_TEST VALUES (1);
          register: exasol_script_simple

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_simple }}"
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
        f"CREATE TABLE {context.test_schema}.SCRIPT_TEST (ID DECIMAL(18, 0))",
        f"INSERT INTO {context.test_schema}.SCRIPT_TEST VALUES (1)",
    ]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == expected_queries

    connection = connect_to_exasol(context.login_vars)
    try:
        rows = connection.execute(
            f"SELECT ID FROM {context.test_schema}.SCRIPT_TEST"
        ).fetchall()
    finally:
        connection.close()

    assert [_row_value(row, "ID", 0) for row in rows] == [1]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-script-body-with-slash-terminator")
def test_exasol_script_execute_script_body_with_slash_terminator(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Execute a script body terminated by a standalone slash line
      block:
        - name: Given the target schema exists
          exasol.exasol.exasol_query:
            query: CREATE SCHEMA {{ test_schema }}

        - name: When exasol_script runs a CREATE SCRIPT body with embedded semicolons
          exasol.exasol.exasol_script:
            script: |
              CREATE SCRIPT {{ test_schema }}.DOUBLE_VALUE AS
              x = 1; y = 2
              /
          register: exasol_script_body

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_body }}"
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

    assert module_result["changed"] is True
    assert len(module_result["executed_queries"]) == 1
    assert "x = 1; y = 2" in module_result["executed_queries"][0]

    connection = connect_to_exasol(context.login_vars)
    try:
        rows = connection.execute(
            "SELECT COUNT(*) AS SCRIPT_COUNT FROM EXA_ALL_SCRIPTS "
            f"WHERE SCHEMA_NAME = '{context.test_schema}' "
            "AND SCRIPT_NAME = 'DOUBLE_VALUE'"
        ).fetchall()
    finally:
        connection.close()

    assert int(_row_value(rows[0], "SCRIPT_COUNT", 0)) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-read-only-script-reports-unchanged")
def test_exasol_script_read_only_script_reports_unchanged(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Read-only script reports unchanged
      block:
        - name: When exasol_script runs a script containing only SELECT statements
          exasol.exasol.exasol_script:
            script: |
              SELECT 1 AS A;
              SELECT 2 AS B;
          register: exasol_script_read_only

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_read_only }}"
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

    assert module_result["changed"] is False
    assert module_result["executed_queries"] == ["SELECT 1 AS A", "SELECT 2 AS B"]
    assert module_result["query_result"] == [{"B": 2}]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-failing-statement-blocks-later-statements")
def test_exasol_script_failing_statement_blocks_later_statements(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Failing statement blocks later statements
      block:
        - name: When exasol_script runs a script whose second statement fails
          exasol.exasol.exasol_script:
            script: |
              CREATE SCHEMA {{ test_schema }};
              SELECT 1 FROM NO_SUCH_TABLE_AT_ALL;
              CREATE TABLE {{ test_schema }}.NEVER_CREATED (ID DECIMAL(18, 0));
          register: exasol_script_failing
          ignore_errors: true

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_failing }}"
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
    assert "NO_SUCH_TABLE_AT_ALL" in module_result["msg"]

    connection = connect_to_exasol(context.login_vars)
    try:
        schema_rows = connection.execute(
            "SELECT COUNT(*) AS SCHEMA_COUNT FROM EXA_ALL_SCHEMAS "
            f"WHERE SCHEMA_NAME = '{context.test_schema}'"
        ).fetchall()
        table_rows = connection.execute(
            "SELECT COUNT(*) AS TABLE_COUNT FROM EXA_ALL_TABLES "
            f"WHERE SCHEMA_NAME = '{context.test_schema}' "
            "AND TABLE_NAME = 'NEVER_CREATED'"
        ).fetchall()
    finally:
        connection.close()

    assert int(_row_value(schema_rows[0], "SCHEMA_COUNT", 0)) == 1
    assert int(_row_value(table_rows[0], "TABLE_COUNT", 0)) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-check-mode-read-only-script")
def test_exasol_script_check_mode_read_only_script(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Check mode keeps a read-only script on the execution path
      block:
        - name: When exasol_script runs a read-only script in check mode
          exasol.exasol.exasol_script:
            script: |
              SELECT 13 AS A;
          check_mode: true
          register: exasol_script_check_mode_read_only

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_check_mode_read_only }}"
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

    assert module_result["changed"] is False
    assert module_result["query_result"] == [{"A": 13}]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-check-mode-write-script")
def test_exasol_script_check_mode_write_script(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Check mode predicts a write script without executing it
      block:
        - name: When exasol_script predicts a schema-creating script in check mode
          exasol.exasol.exasol_script:
            script: |
              CREATE SCHEMA {{ check_mode_schema }};
          check_mode: true
          register: exasol_script_check_mode_write

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_check_mode_write }}"
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
    expected_script = f"CREATE SCHEMA {context.check_mode_schema};\n"

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [expected_script]
    assert module_result["query_result"] == []

    connection = connect_to_exasol(context.login_vars)
    try:
        rows = connection.execute(
            "SELECT COUNT(*) AS SCHEMA_COUNT FROM EXA_ALL_SCHEMAS "
            f"WHERE SCHEMA_NAME = '{context.check_mode_schema}'"
        ).fetchall()
    finally:
        connection.close()

    assert int(_row_value(rows[0], "SCHEMA_COUNT", 0)) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-sanitize-bad-credentials")
def test_exasol_script_sanitize_bad_credentials(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Sanitize bad credential errors
      block:
        - name: When exasol_script runs with bad credentials
          exasol.exasol.exasol_script:
            login_host: "{{ login_host }}"
            login_port: "{{ login_port }}"
            login_user: "{{ login_user }}"
            login_password: "{{ invalid_login_password }}"
            validate_certs: "{{ validate_certs }}"
            certificate_fingerprint: "{{ certificate_fingerprint | default('') }}"
            script: SELECT 1 AS A;
          register: exasol_script_bad_credentials
          ignore_errors: true

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_bad_credentials }}"
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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-reject-unsupported-bound-arguments")
def test_exasol_script_reject_unsupported_bound_arguments(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Reject unsupported bound arguments
      block:
        - name: When exasol_script runs with a positional_args argument
          exasol.exasol.exasol_script:
            script: SELECT ? AS A
            positional_args:
              - 42
          register: exasol_script_bound_args
          ignore_errors: true

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_script_bound_args }}"
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
    assert "positional_args" in module_result["msg"]


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[key]

    return row[index]
