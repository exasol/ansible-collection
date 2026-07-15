"""Playbook-backed tests for exasol-init feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    given_acceptance_context,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)

MODULE_NAME = "exasol_init"


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_full_environment_happy_path(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-full-environment-happy-path"

    playbook = """
    - name: Initialize a full environment in dependency order
      block:
        - name: When exasol_init runs with roles, users, grants, schemas, and scripts
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
            role_grants:
              - role: "{{ test_role }}"
                user: "{{ test_user }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ test_user }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"
            scripts:
              - "CREATE TABLE {{ test_schema }}.EVENTS (ID INT)"
          register: exasol_init_full

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_full }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'CREATE ROLE "{context.test_role}"',
        f'CREATE USER "{context.test_user}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{context.test_user}"',
        f'GRANT "{context.test_role}" TO "{context.test_user}"',
        f'CREATE SCHEMA "{context.test_schema}"',
        f'ALTER SCHEMA "{context.test_schema}" CHANGE OWNER "{context.test_user}"',
        f'GRANT SELECT ON SCHEMA "{context.test_schema}" TO "{context.test_role}"',
        f"CREATE TABLE {context.test_schema}.EVENTS (ID INT)",
    ]

    then_secret_is_not_exposed(result, context.test_user_password)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_schema_owner_assigned_after_user_created(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-schema-owner-assigned-after-user-created"

    playbook = """
    - name: Schema owner reassignment depends only on the owning user
      block:
        - name: When exasol_init runs with a user and a schema owned by that user
          exasol.exasol.exasol_init:
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ test_user }}"
          register: exasol_init_owner

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_owner }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'CREATE USER "{context.test_user}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{context.test_user}"',
        f'CREATE SCHEMA "{context.test_schema}"',
        f'ALTER SCHEMA "{context.test_schema}" CHANGE OWNER "{context.test_user}"',
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_grants_wait_for_roles_users_and_schemas(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-grants-wait-for-roles-users-and-schemas"

    playbook = """
    - name: Schema privilege grants only run once their role and schema exist
      block:
        - name: When exasol_init runs with a role, a schema, and a grant between them
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            schemas:
              - name: "{{ test_schema }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"
          register: exasol_init_grants_join

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_grants_join }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'CREATE ROLE "{context.test_role}"',
        f'CREATE SCHEMA "{context.test_schema}"',
        f'GRANT SELECT ON SCHEMA "{context.test_schema}" TO "{context.test_role}"',
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_scripts_run_after_grants(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-scripts-run-after-grants"

    playbook = """
    - name: Init scripts execute only after grants are applied
      block:
        - name: When exasol_init runs with a role, a schema, a grant, and a script
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            schemas:
              - name: "{{ test_schema }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"
            scripts:
              - "CREATE TABLE {{ test_schema }}.ARTICLES (ID INT)"
          register: exasol_init_scripts_after_grants

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_scripts_after_grants }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"][-1] == (
        f"CREATE TABLE {context.test_schema}.ARTICLES (ID INT)"
    )
    assert module_result["executed_queries"][:-1] == [
        f'CREATE ROLE "{context.test_role}"',
        f'CREATE SCHEMA "{context.test_schema}"',
        f'GRANT SELECT ON SCHEMA "{context.test_schema}" TO "{context.test_role}"',
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_apply_unchanged_is_idempotent(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-apply-unchanged-is-idempotent"

    playbook = """
    - name: Re-applying an identical environment makes no further changes
      block:
        - name: Given a full environment already exists
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
            role_grants:
              - role: "{{ test_role }}"
                user: "{{ test_user }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ test_user }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"

        - name: When exasol_init runs again with the same parameters
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
                update_password: on_create
            role_grants:
              - role: "{{ test_role }}"
                user: "{{ test_user }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ test_user }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"
          register: exasol_init_repeat

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_repeat }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is False
    assert module_result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_check_mode_predicts_full_plan(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-check-mode-predicts-full-plan"

    playbook = """
    - name: Check mode predicts the full ordered plan without writing
      block:
        - name: When exasol_init runs in check mode with a full environment
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ check_mode_role }}"
            users:
              - name: "{{ check_mode_user }}"
                password: "{{ check_mode_user_password }}"
            role_grants:
              - role: "{{ check_mode_role }}"
                user: "{{ check_mode_user }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ check_mode_user }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ check_mode_role }}"
            scripts:
              - "CREATE TABLE {{ test_schema }}.T (ID INT)"
          check_mode: true
          register: exasol_init_check_plan

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_check_plan }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'CREATE ROLE "{context.check_mode_role}"',
        f'CREATE USER "{context.check_mode_user}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{context.check_mode_user}"',
        f'GRANT "{context.check_mode_role}" TO "{context.check_mode_user}"',
        f'CREATE SCHEMA "{context.test_schema}"',
        f'ALTER SCHEMA "{context.test_schema}" CHANGE OWNER "{context.check_mode_user}"',
        f'GRANT SELECT ON SCHEMA "{context.test_schema}" TO "{context.check_mode_role}"',
        f"CREATE TABLE {context.test_schema}.T (ID INT)",
    ]

    then_secret_is_not_exposed(result, context.check_mode_user_password)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_partial_environment_roles_and_users_only(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-partial-environment-roles-and-users-only"

    playbook = """
    - name: Optional phases are skipped when their parameters are omitted
      block:
        - name: When exasol_init runs with only roles and users
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
          register: exasol_init_partial

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_partial }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'CREATE ROLE "{context.test_role}"',
        f'CREATE USER "{context.test_user}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{context.test_user}"',
    ]
    assert module_result["schemas"] == []
    assert module_result["grants"] == []
    assert module_result["scripts"] == {"changed": False, "executed_queries": []}


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_teardown_drops_in_reverse_dependency_order(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-teardown-drops-in-reverse-dependency-order"

    playbook = """
    - name: Tearing down an environment reverses the dependency order
      block:
        - name: Given a full environment already exists
          exasol.exasol.exasol_init:
            roles:
              - name: "{{ test_role }}"
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
            role_grants:
              - role: "{{ test_role }}"
                user: "{{ test_user }}"
            schemas:
              - name: "{{ test_schema }}"
                owner: "{{ test_user }}"
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"

        - name: When exasol_init tears the environment back down
          exasol.exasol.exasol_init:
            grants:
              - schema: "{{ test_schema }}"
                privilege: SELECT
                grantee: "{{ test_role }}"
                state: absent
            role_grants:
              - role: "{{ test_role }}"
                user: "{{ test_user }}"
                state: absent
            schemas:
              - name: "{{ test_schema }}"
                state: absent
                cascade: true
            users:
              - name: "{{ test_user }}"
                state: absent
                cascade: true
            roles:
              - name: "{{ test_role }}"
                state: absent
                cascade: true
          register: exasol_init_teardown

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_teardown }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    assert module_result["executed_queries"] == [
        f'REVOKE SELECT ON SCHEMA "{context.test_schema}" FROM "{context.test_role}"',
        f'REVOKE "{context.test_role}" FROM "{context.test_user}"',
        f'DROP SCHEMA "{context.test_schema}" CASCADE',
        f'DROP USER "{context.test_user}" CASCADE',
        f'DROP ROLE "{context.test_role}" CASCADE',
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_init_secrets_are_not_exposed(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    scenario_id = "exasol-init-secrets-are-not-exposed"

    playbook = """
    - name: Passwords and LDAP distinguished names are never exposed
      block:
        - name: When exasol_init runs with a password user and an LDAP user
          exasol.exasol.exasol_init:
            users:
              - name: "{{ test_user }}"
                password: "{{ test_user_password }}"
              - name: "{{ check_mode_user }}"
                authentication_method: ldap
                ldap_dn: "{{ check_mode_user_ldap_dn }}"
          register: exasol_init_secrets

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_init_secrets }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )
    module_result = result["module_result"]

    assert module_result["changed"] is True
    then_secret_is_not_exposed(result, context.test_user_password)
    then_secret_is_not_exposed(result, context.check_mode_user_ldap_dn)
