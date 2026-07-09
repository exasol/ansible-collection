"""Playbook-backed tests for exasol-role feature scenarios."""

from __future__ import annotations

import re
from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    connect_to_exasol,
    given_acceptance_context,
    when_module_scenario_runs,
)

from exasol.ansible_modules.common_identifier_validation import quote_exact_identifier
from exasol.ansible_modules.common_query import normalized_exasol_error_message

MODULE_NAME = "exasol_role"
DISPOSABLE_ROLE_PATTERN = re.compile(r"^ANSIBLE_ROLE(?:_CHECK)?_[0-9A-F]{32}$")
DISPOSABLE_EXACT_ROLE_PATTERN = re.compile(r"^Ansible\+/=Role_[0-9A-F]{32}$")


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_create_missing_role(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Create missing role."""
    scenario_id = "exasol-role-create-missing-role"
    playbook = """
    - name: Create missing role
      block:
        - name: Given a disposable Exasol role does not exist
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
            state: absent
            cascade: true

        - name: When the exasol_role module runs with state present
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
          register: exasol_role_create

        - name: Read role metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS ROLE_COUNT
              FROM EXA_ALL_ROLES
              WHERE ROLE_NAME = :role_name
            named_args:
              role_name: "{{ test_role }}"
          register: exasol_role_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_create }}"
              metadata_result: "{{ exasol_role_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=True,
        role=context.test_role,
        state="present",
        exists=True,
        executed_queries=[_create_role_query(context.test_role)],
    )
    _assert_role_count(result["metadata_result"], 1)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_preserves_exact_identifier(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Create role with exact identifier semantics."""
    scenario_id = "exasol-role-preserves-exact-identifier"
    playbook = """
    - name: Preserve exact role identifier
      block:
        - name: Given an exact-identifier Exasol role does not exist
          exasol.exasol.exasol_role:
            name: "{{ exact_test_role }}"
            state: absent
            cascade: true

        - name: When the exasol_role module runs with an exact identifier value
          exasol.exasol.exasol_role:
            name: "{{ exact_test_role }}"
          register: exasol_role_exact

        - name: Read role metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS ROLE_COUNT
              FROM EXA_ALL_ROLES
              WHERE UPPER(ROLE_NAME) = UPPER(:role_name)
            named_args:
              role_name: "{{ exact_test_role }}"
          register: exasol_role_exact_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_exact }}"
              metadata_result: "{{ exasol_role_exact_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=True,
        role=context.exact_test_role,
        state="present",
        exists=True,
        executed_queries=[_create_role_query(context.exact_test_role)],
    )
    _assert_role_count(result["metadata_result"], 1)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_present_idempotent(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Present role is idempotent."""
    scenario_id = "exasol-role-present-idempotent"
    playbook = """
    - name: Present role is idempotent
      block:
        - name: Given a disposable Exasol role already exists
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"

        - name: When the exasol_role module is re-run with the same parameters
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
          register: exasol_role_existing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_existing }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=False,
        role=context.test_role,
        state="present",
        exists=True,
        executed_queries=[],
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_present_idempotent_with_different_case_spelling(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Present role stays idempotent across case-only spelling changes."""
    scenario_id = "exasol-role-present-idempotent-with-different-case-spelling"
    playbook = """
    - name: Present role with different case spelling is idempotent
      block:
        - name: Given an exact-identifier Exasol role already exists
          exasol.exasol.exasol_role:
            name: "{{ exact_test_role }}"

        - name: When the exasol_role module is re-run with a different case spelling
          exasol.exasol.exasol_role:
            name: "{{ exact_test_role | lower }}"
          register: exasol_role_existing_different_case

        - name: Read role metadata after the case-variant run
          exasol.exasol.exasol_query:
            query: >-
              SELECT ROLE_NAME
              FROM EXA_ALL_ROLES
              WHERE UPPER(ROLE_NAME) = UPPER(:role_name)
            named_args:
              role_name: "{{ exact_test_role }}"
          register: exasol_role_case_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_existing_different_case }}"
              metadata_result: "{{ exasol_role_case_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=False,
        role=context.exact_test_role.lower(),
        state="present",
        exists=True,
        executed_queries=[],
    )
    _assert_stored_role_name(result["metadata_result"], context.exact_test_role.upper())


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_check_mode_create(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts create."""
    scenario_id = "exasol-role-check-mode-create"
    playbook = """
    - name: Check mode predicts create
      block:
        - name: Given a disposable Exasol role does not exist
          exasol.exasol.exasol_role:
            name: "{{ check_mode_role }}"
            state: absent
            cascade: true

        - name: When the exasol_role module predicts create in check mode
          exasol.exasol.exasol_role:
            name: "{{ check_mode_role }}"
          check_mode: true
          register: exasol_role_check_create

        - name: Read check-mode role metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS ROLE_COUNT
              FROM EXA_ALL_ROLES
              WHERE ROLE_NAME = :role_name
            named_args:
              role_name: "{{ check_mode_role }}"
          register: exasol_role_check_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_check_create }}"
              metadata_result: "{{ exasol_role_check_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=True,
        role=context.check_mode_role,
        state="present",
        exists=True,
        executed_queries=[_create_role_query(context.check_mode_role)],
    )
    _assert_role_count(result["metadata_result"], 0)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_check_mode_drop(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts drop."""
    scenario_id = "exasol-role-check-mode-drop"
    playbook = """
    - name: Check mode predicts drop
      block:
        - name: Given a disposable Exasol role exists
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"

        - name: When the exasol_role module predicts drop in check mode
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
            state: absent
            cascade: true
          check_mode: true
          register: exasol_role_check_drop

        - name: Read check-mode role metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS ROLE_COUNT
              FROM EXA_ALL_ROLES
              WHERE ROLE_NAME = :role_name
            named_args:
              role_name: "{{ test_role }}"
          register: exasol_role_check_drop_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_check_drop }}"
              metadata_result: "{{ exasol_role_check_drop_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=True,
        role=context.test_role,
        state="absent",
        exists=False,
        executed_queries=[_drop_role_query(context.test_role)],
    )
    _assert_role_count(result["metadata_result"], 1)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_drop_existing_role(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Drop existing role."""
    scenario_id = "exasol-role-drop-existing-role"
    playbook = """
    - name: Drop existing role
      block:
        - name: Given a disposable Exasol role exists
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"

        - name: When the exasol_role module runs with state absent and cascade
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
            state: absent
            cascade: true
          register: exasol_role_drop

        - name: Read role metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT COUNT(*) AS ROLE_COUNT
              FROM EXA_ALL_ROLES
              WHERE ROLE_NAME = :role_name
            named_args:
              role_name: "{{ test_role }}"
          register: exasol_role_drop_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_drop }}"
              metadata_result: "{{ exasol_role_drop_metadata }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=True,
        role=context.test_role,
        state="absent",
        exists=False,
        executed_queries=[_drop_role_query(context.test_role)],
    )
    _assert_role_count(result["metadata_result"], 0)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_role_drop_missing_role(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Drop missing role."""
    scenario_id = "exasol-role-drop-missing-role"
    playbook = """
    - name: Drop missing role
      block:
        - name: Given a disposable Exasol role does not exist
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
            state: absent
            cascade: true

        - name: When the exasol_role module runs with state absent
          exasol.exasol.exasol_role:
            name: "{{ test_role }}"
            state: absent
          register: exasol_role_drop_missing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_role_drop_missing }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_role_scenario_runs(context, scenario_id, playbook)

    _assert_role_module_result(
        result["module_result"],
        changed=False,
        role=context.test_role,
        state="absent",
        exists=False,
        executed_queries=[],
    )


def _when_role_scenario_runs(
    context: Any,
    scenario_id: str,
    playbook: str,
) -> dict[str, Any]:
    scenario_error = None
    try:
        return when_module_scenario_runs(
            context,
            MODULE_NAME,
            scenario_id,
            scenario_playbook=playbook,
        )
    except Exception as error:
        scenario_error = error
        raise
    finally:
        try:
            _cleanup_disposable_roles(context)
        except Exception:
            if scenario_error is None:
                raise


def _assert_role_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    role: str,
    state: str,
    exists: bool,
    executed_queries: list[str],
) -> None:
    assert result["changed"] is changed
    assert result["failed"] is False
    assert result["role"] == role
    assert result["state"] == state
    assert result["exists"] is exists
    assert result["executed_queries"] == executed_queries


def _assert_role_count(result: dict[str, Any], expected: int) -> None:
    assert result["failed"] is False
    assert int(result["query_result"][0]["ROLE_COUNT"]) == expected


def _assert_stored_role_name(result: dict[str, Any], expected_role_name: str) -> None:
    assert result["failed"] is False
    assert result["query_result"] == [{"ROLE_NAME": expected_role_name}]


def _cleanup_disposable_roles(context: Any) -> None:
    role_names = (context.test_role, context.check_mode_role, context.exact_test_role)
    for role_name in role_names:
        _assert_disposable_role_name(role_name)

    try:
        connection = connect_to_exasol(context.login_vars)
        try:
            for role_name in role_names:
                if _role_exists(connection, role_name):
                    connection.execute(
                        f"DROP ROLE {quote_exact_identifier(role_name)} CASCADE"
                    )
        finally:
            connection.close()
    except Exception as error:
        message = normalized_exasol_error_message(
            error,
            context.login_vars,
            operation="Acceptance role cleanup",
        )
        raise AssertionError(message) from error


def _role_exists(connection: Any, role_name: str) -> bool:
    rows = connection.execute(f"""
        SELECT COUNT(*) AS ROLE_COUNT
        FROM EXA_ALL_ROLES
        WHERE UPPER(ROLE_NAME) = UPPER('{role_name}')
        """).fetchall()
    return int(_row_value(rows[0], "ROLE_COUNT", 0)) > 0


def _assert_disposable_role_name(role_name: str) -> None:
    if not (
        DISPOSABLE_ROLE_PATTERN.fullmatch(role_name)
        or DISPOSABLE_EXACT_ROLE_PATTERN.fullmatch(role_name)
    ):
        msg = f"Unsafe disposable acceptance role name: {role_name}"
        raise AssertionError(msg)


def _create_role_query(role_name: str) -> str:
    return f"CREATE ROLE {quote_exact_identifier(role_name)}"


def _drop_role_query(role_name: str) -> str:
    return f"DROP ROLE {quote_exact_identifier(role_name)} CASCADE"


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[key]

    return row[index]
