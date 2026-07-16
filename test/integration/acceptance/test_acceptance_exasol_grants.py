"""Playbook-backed tests for exasol-grants feature scenarios."""

from __future__ import annotations

from test.integration.acceptance_common.acceptance_test_common import (
    connect_to_exasol,
    given_acceptance_context,
    when_module_scenario_runs,
)
from typing import Any

import pytest

from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier,
    quote_identifier,
)

MODULE_NAME = "exasol_grants"


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_grant_missing_system_privilege(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Grant missing system privilege."""
    scenario_id = "exasol-grants-grant-missing-system-privilege"
    playbook = """
    - name: Grant missing system privilege
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: When exasol_grants grants CREATE SESSION
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            system_privileges:
              - CREATE SESSION
          register: exasol_grants_system_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_system_create }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=True,
        principal=context.test_user,
        principal_type="user",
        state="present",
        executed_queries=[_grant_system_query("CREATE SESSION", context.test_user)],
    )
    assert (
        _system_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            privilege="CREATE SESSION",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_system_privilege_idempotent(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Existing system privilege is unchanged."""
    scenario_id = "exasol-grants-system-privilege-idempotent"
    playbook = """
    - name: Existing system privilege is unchanged
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: Given CREATE SESSION was granted directly
          exasol.exasol.exasol_query:
            query: GRANT CREATE SESSION TO "{{ test_user }}"

        - name: When exasol_grants is re-run for CREATE SESSION
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            system_privileges:
              - CREATE SESSION
          register: exasol_grants_system_existing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_system_existing }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=False,
        principal=context.test_user,
        principal_type="user",
        state="present",
        executed_queries=[],
    )
    assert (
        _system_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            privilege="CREATE SESSION",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_grant_multiple_system_and_object_privileges(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Grant multiple system and object privileges."""
    scenario_id = "exasol-grants-grant-multiple-system-and-object-privileges"
    playbook = """
    - name: Grant multiple system and object privileges
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: Given a schema and table exist
          exasol.exasol.exasol_query:
            query:
              - CREATE SCHEMA {{ test_schema }}
              - CREATE TABLE {{ test_schema }}.FACT_SALES (ID DECIMAL(18,0))

        - name: When exasol_grants grants multiple privileges
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            system_privileges:
              - CREATE SESSION
              - CREATE SCHEMA
            object_privileges:
              - schema: "{{ test_schema }}"
                privileges:
                  - USAGE
              - schema: "{{ test_schema }}"
                object: FACT_SALES
                privileges:
                  - SELECT
                  - INSERT
          register: exasol_grants_multi_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_multi_create }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=True,
        principal=context.test_user,
        principal_type="user",
        state="present",
        executed_queries=[
            _grant_system_query("CREATE SESSION", context.test_user),
            _grant_system_query("CREATE SCHEMA", context.test_user),
            _grant_schema_query("USAGE", context.test_schema, context.test_user),
            _grant_object_query(
                "SELECT",
                context.test_schema,
                "FACT_SALES",
                context.test_user,
            ),
            _grant_object_query(
                "INSERT",
                context.test_schema,
                "FACT_SALES",
                context.test_user,
            ),
        ],
    )
    assert (
        _system_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            privilege="CREATE SESSION",
        )
        == 1
    )
    assert (
        _system_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            privilege="CREATE SCHEMA",
        )
        == 1
    )
    assert (
        _schema_object_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            schema_name=context.test_schema,
            privilege="USAGE",
        )
        == 1
    )
    assert (
        _object_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            schema_name=context.test_schema,
            object_name="FACT_SALES",
            privilege="SELECT",
        )
        == 1
    )
    assert (
        _object_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            schema_name=context.test_schema,
            object_name="FACT_SALES",
            privilege="INSERT",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_revoke_existing_schema_object_privilege(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Revoke existing schema object privilege."""
    scenario_id = "exasol-grants-revoke-existing-schema-object-privilege"
    playbook = """
    - name: Revoke existing schema object privilege
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: Given schema USAGE was granted directly
          exasol.exasol.exasol_query:
            query:
              - CREATE SCHEMA {{ test_schema }}
              - GRANT USAGE ON {{ test_schema }} TO "{{ test_user }}"

        - name: When exasol_grants revokes schema USAGE
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            state: absent
            object_privileges:
              - schema: "{{ test_schema }}"
                privileges:
                  - USAGE
          register: exasol_grants_schema_revoke

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_schema_revoke }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=True,
        principal=context.test_user,
        principal_type="user",
        state="absent",
        executed_queries=[
            _revoke_schema_query("USAGE", context.test_schema, context.test_user)
        ],
    )
    assert (
        _schema_object_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            schema_name=context.test_schema,
            privilege="USAGE",
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_absent_schema_object_privilege_idempotent(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Missing schema object privilege is unchanged when absent."""
    scenario_id = "exasol-grants-absent-schema-object-privilege-idempotent"
    playbook = """
    - name: Missing schema object privilege is unchanged when absent
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: Given the schema exists
          exasol.exasol.exasol_query:
            query: CREATE SCHEMA {{ test_schema }}

        - name: When exasol_grants revokes missing schema USAGE
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            state: absent
            object_privileges:
              - schema: "{{ test_schema }}"
                privileges:
                  - USAGE
          register: exasol_grants_schema_absent

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_schema_absent }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=False,
        principal=context.test_user,
        principal_type="user",
        state="absent",
        executed_queries=[],
    )
    assert (
        _schema_object_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            schema_name=context.test_schema,
            privilege="USAGE",
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_check_mode_predicts_system_grant(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts system grant."""
    scenario_id = "exasol-grants-check-mode-predicts-system-grant"
    playbook = """
    - name: Check mode predicts system grant
      block:
        - name: Given an Exasol user exists without CREATE SESSION
          exasol.exasol.exasol_user:
            name: "{{ test_user }}"
            password: "{{ test_user_password }}"
            create_session: false

        - name: When exasol_grants predicts CREATE SESSION in check mode
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            system_privileges:
              - CREATE SESSION
          check_mode: true
          register: exasol_grants_system_check

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_system_check }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)

    _assert_grants_module_result(
        result["module_result"],
        changed=True,
        principal=context.test_user,
        principal_type="user",
        state="present",
        executed_queries=[_grant_system_query("CREATE SESSION", context.test_user)],
    )
    assert (
        _system_privilege_count(
            context.login_vars,
            grantee=context.test_user,
            privilege="CREATE SESSION",
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_grants_reject_mutually_exclusive_principals(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Reject mutually exclusive principals."""
    scenario_id = "exasol-grants-reject-mutually-exclusive-principals"
    playbook = """
    - name: Reject mutually exclusive principals
      block:
        - name: When exasol_grants receives both principal parameters
          exasol.exasol.exasol_grants:
            user: "{{ test_user }}"
            role: "{{ test_role }}"
            system_privileges:
              - CREATE SESSION
          register: exasol_grants_bad_principal
          ignore_errors: true

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_grants_bad_principal }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_grants_scenario_runs(context, scenario_id, playbook)
    module_result = result["module_result"]

    assert module_result["failed"] is True
    assert "mutually exclusive" in module_result["msg"]
    assert module_result["changed"] is False
    assert "executed_queries" not in module_result


def _when_grants_scenario_runs(
    context: Any,
    scenario_id: str,
    playbook: str,
) -> dict[str, Any]:
    return when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )


def _assert_grants_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    principal: str,
    principal_type: str,
    state: str,
    executed_queries: list[str],
) -> None:
    assert result["changed"] is changed
    assert result["failed"] is False
    assert result["principal"] == principal
    assert result["principal_type"] == principal_type
    assert result["state"] == state
    assert result["executed_queries"] == executed_queries


def _grant_system_query(privilege: str, principal: str) -> str:
    return f"GRANT {privilege} TO {quote_exact_identifier(principal)}"


def _grant_schema_query(privilege: str, schema_name: str, principal: str) -> str:
    return (
        f"GRANT {privilege} ON {quote_identifier(schema_name)} "
        f"TO {quote_exact_identifier(principal)}"
    )


def _grant_object_query(
    privilege: str,
    schema_name: str,
    object_name: str,
    principal: str,
) -> str:
    return (
        f"GRANT {privilege} ON {quote_identifier(schema_name)}."
        f"{quote_identifier(object_name)} TO {quote_exact_identifier(principal)}"
    )


def _revoke_schema_query(privilege: str, schema_name: str, principal: str) -> str:
    return (
        f"REVOKE {privilege} ON {quote_identifier(schema_name)} "
        f"FROM {quote_exact_identifier(principal)}"
    )


def _system_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    privilege: str,
) -> int:
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_SYS_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        """,
    )


def _schema_object_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    schema_name: str,
    privilege: str,
) -> int:
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_OBJ_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        AND UPPER(COALESCE(OBJECT_SCHEMA, OBJECT_NAME)) =
            UPPER({_quote_sql_literal(schema_name)})
        AND (OBJECT_NAME IS NULL OR UPPER(OBJECT_NAME) =
            UPPER({_quote_sql_literal(schema_name)}))
        """,
    )


def _object_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    schema_name: str,
    object_name: str,
    privilege: str,
) -> int:
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_OBJ_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        AND UPPER(OBJECT_SCHEMA) = UPPER({_quote_sql_literal(schema_name)})
        AND UPPER(OBJECT_NAME) = UPPER({_quote_sql_literal(object_name)})
        """,
    )


def _metadata_count(login_vars: dict[str, object], query: str) -> int:
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()

    return int(_row_value(rows[0], "PRIVILEGE_COUNT", 0))


def _quote_sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]

    return row[index]
