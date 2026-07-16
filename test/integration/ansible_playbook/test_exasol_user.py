"""Playbook-backed tests for exasol-user feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    given_acceptance_context,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)
from acceptance_common.test_common_user import assert_user_can_log_in

MODULE_NAME = "exasol_user"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-create-missing-user")
def test_exasol_user_create_missing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Create missing user
      block:
        - name: Given an Exasol user does not exist
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            state: absent
            cascade: true

        - name: When the exasol_user module runs with state present and a password
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
          register: exasol_user_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_create }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        user=context.test_user,
        exists=True,
        executed_queries_len=2,
    )

    then_secret_is_not_exposed(result, context.test_user_password)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-preserves-exact-identifier")
def test_exasol_user_preserves_exact_identifier(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Preserve exact user identifier
      block:
        - name: Given an exact-identifier user does not exist
          exasol.exasol.exasol_user:
            name: "{{ exact_test_user }}"
            state: absent
            cascade: true

        - name: When the exasol_user module runs with an exact identifier value
          exasol.exasol.exasol_user:
            name: "{{ exact_test_user }}"
            password: "{{ test_user_password }}"
          register: exasol_user_exact_identifier

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_exact_identifier }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        user=context.exact_test_user,
        exists=True,
        executed_queries_len=2,
    )
    assert result["module_result"]["executed_queries"][0].startswith(
        f'CREATE USER "{context.exact_test_user}"'
    )

    then_secret_is_not_exposed(result, context.test_user_password)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-apply-unchanged")
def test_exasol_user_apply_unchanged(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Applying identical user state results in no changes
      block:
        - name: Given an Exasol user already exists
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module runs with update_password on_create
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            update_password: on_create
          register: exasol_user_existing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_existing }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=False,
        exists=True,
        executed_queries_len=0,
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-apply-unchanged-with-different-case-spelling")
def test_exasol_user_apply_unchanged_with_different_case_spelling(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Applying same user with different case spelling stays idempotent
      block:
        - name: Given an exact-identifier Exasol user already exists
          exasol.exasol.exasol_user:
            name: "{{ exact_test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module runs with a different case spelling
          exasol.exasol.exasol_user:
            name: "{{ exact_test_user | lower }}"
            password: "{{ test_user_password }}"
            update_password: on_create
          register: exasol_user_existing_different_case

        - name: Read user metadata after the case-variant run
          exasol.exasol.exasol_query:
            query: >-
              SELECT USER_NAME
              FROM EXA_DBA_USERS
              WHERE UPPER(USER_NAME) = UPPER(:user_name)
            named_args:
              user_name: "{{ exact_test_user }}"
          register: exasol_user_case_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_existing_different_case }}"
              metadata_result: "{{ exasol_user_case_metadata }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=False,
        user=context.exact_test_user.lower(),
        exists=True,
        executed_queries_len=0,
    )
    _assert_stored_user_name(result["metadata_result"], context.exact_test_user.upper())


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-change-authentication-to-ldap")
def test_exasol_user_change_authentication_to_ldap(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Change authentication to LDAP
      block:
        - name: Given an Exasol password-authenticated user already exists
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module runs with LDAP authentication
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            authentication_method: ldap
            ldap_dn: "{{ test_user_ldap_dn }}"
          register: exasol_user_ldap

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_ldap }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        exists=True,
        executed_queries_len=1,
    )

    then_secret_is_not_exposed(result, context.test_user_ldap_dn)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-rotate-password")
def test_exasol_user_rotate_password(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Rotate password
      block:
        - name: Given a user exists with password authentication and initial password
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When exasol_user runs with update_password always and a new password
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_rotated_password }}"
            update_password: always
          register: exasol_user_rotate

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_rotate }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        exists=True,
        executed_queries_len=1,
    )
    assert_user_can_log_in(
        context.login_vars, context.test_user, context.test_user_rotated_password
    )

    then_secret_is_not_exposed(result, context.test_user_password)
    then_secret_is_not_exposed(result, context.test_user_rotated_password)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-check-mode-create")
def test_exasol_user_check_mode_create(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Check mode predicts create
      block:
        - name: Given an Exasol user does not exist
          exasol.exasol.exasol_user:
            name: "{{ check_mode_user }}"
            state: absent
            cascade: true

        - name: When the exasol_user module runs in check mode with state present
          exasol.exasol.exasol_user:
            name: "{{ check_mode_user }}"
            password: "{{ check_mode_user_password }}"
          check_mode: true
          register: exasol_user_check_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_check_create }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        user=context.check_mode_user,
        exists=True,
        executed_queries_len=2,
    )

    then_secret_is_not_exposed(result, context.check_mode_user_password)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-check-mode-update-ldap")
def test_exasol_user_check_mode_update_ldap(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Check mode predicts LDAP update
      block:
        - name: Given an Exasol password-authenticated user already exists
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module predicts LDAP authentication in check mode
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            authentication_method: ldap
            ldap_dn: "{{ check_mode_user_ldap_dn }}"
          check_mode: true
          register: exasol_user_check_ldap

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_check_ldap }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        exists=True,
        executed_queries_len=1,
    )

    # IMPORTANT: LDAP DN must not be exposed even in check mode
    then_secret_is_not_exposed(result, context.check_mode_user_ldap_dn)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-check-mode-drop")
def test_exasol_user_check_mode_drop(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Check mode predicts drop
      block:
        - name: Given an Exasol user exists
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module predicts drop in check mode
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            state: absent
            cascade: true
          check_mode: true
          register: exasol_user_check_drop

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_check_drop }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        exists=False,
        executed_queries_len=1,
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-drop-existing-user")
def test_exasol_user_drop_existing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Drop existing user
      block:
        - name: Given an Exasol user exists
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"

        - name: When the exasol_user module runs with state absent and cascade
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            state: absent
            cascade: true
          register: exasol_user_drop

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_drop }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=True,
        exists=False,
        executed_queries_len=1,
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-user-drop-missing-user")
def test_exasol_user_drop_missing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    playbook = """
    - name: Drop missing user
      block:
        - name: Given an Exasol user does not exist
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            state: absent
            cascade: true

        - name: When the exasol_user module runs with state absent
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            state: absent
          register: exasol_user_drop_missing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_user_drop_missing }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_user_module_result(
        result["module_result"],
        changed=False,
        exists=False,
        executed_queries_len=0,
    )


# -----------------------
# helpers
# -----------------------


def _assert_user_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    exists: bool | None = None,
    user: str | None = None,
    ldap_dn: str | None = None,
    executed_queries_len: int,
) -> None:
    expected_keys = {
        "changed",
        "executed_queries",
        "exists",
        "failed",
        "ldap_dn",
        "result_json",
        "state",
        "user",
    }

    assert set(result) <= expected_keys
    assert result["changed"] is changed
    assert result["failed"] is False

    if exists is not None:
        assert result["exists"] is exists
        assert result["state"] == ("present" if exists else "absent")
    if user is not None:
        assert result["user"] == user
    else:
        assert isinstance(result["user"], str)
    if ldap_dn is not None:
        assert result["ldap_dn"] == ldap_dn

    executed_queries = result["executed_queries"]
    assert isinstance(executed_queries, list)
    assert len(executed_queries) == executed_queries_len


def _assert_stored_user_name(result: dict[str, Any], expected_user_name: str) -> None:
    assert result["failed"] is False
    assert result["query_result"] == [{"USER_NAME": expected_user_name}]
