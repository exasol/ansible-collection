"""Playbook-backed tests for exasol-schema feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from ansible_playbook.common_helpers import (
    AcceptanceContext,
    connect_to_exasol,
    given_acceptance_context,
    when_module_scenario_runs,
)

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    validate_schema_name,
)

MODULE_NAME = "exasol_schema"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-create-missing-schema")
def test_exasol_schema_create_missing_schema(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Create missing schema."""
    playbook = """
    - name: Create missing schema
      block:
        - name: When exasol_schema runs with state present
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: present
          register: schema_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_create }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        state="present",
        exists=True,
        executed_queries=[_create_schema_query(context.test_schema)],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-preserves-exact-identifier")
def test_exasol_schema_preserves_exact_identifier(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Create schema with exact identifier semantics."""
    playbook = """
    - name: Preserve exact schema identifier
      block:
        - name: When exasol_schema runs with an exact identifier
          exasol.exasol.exasol_schema:
            name: "{{ exact_test_schema }}"
            state: present
          register: schema_exact

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_exact }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.exact_test_schema,
        state="present",
        exists=True,
        executed_queries=[_create_schema_query(context.exact_test_schema)],
    )
    assert _schema_count(context.login_vars, context.exact_test_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-apply-unchanged")
def test_exasol_schema_apply_unchanged(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Applying identical schema state results in no changes."""
    playbook = """
    - name: Apply identical schema state
      block:
        - name: When exasol_schema runs with state present
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: present
          register: schema_existing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_existing }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=False,
        schema=context.test_schema,
        state="present",
        exists=True,
        executed_queries=[],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-apply-unchanged-with-different-case-spelling")
def test_exasol_schema_apply_unchanged_with_different_case_spelling(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Applying a case-only spelling change stays idempotent."""
    playbook = """
    - name: Apply schema with different case spelling
      block:
        - name: When exasol_schema runs with a case-only spelling change
          exasol.exasol.exasol_schema:
            name: "{{ exact_test_schema | lower }}"
            state: present
          register: schema_case_variant

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_case_variant }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.exact_test_schema)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=False,
        schema=context.exact_test_schema.lower(),
        state="present",
        exists=True,
        executed_queries=[],
    )
    assert _stored_schema_names(context.login_vars, context.exact_test_schema) == [
        context.exact_test_schema
    ]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-check-mode-create")
def test_exasol_schema_check_mode_create(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Check mode predicts create."""
    playbook = """
    - name: Check mode predicts create
      block:
        - name: When exasol_schema runs in check mode with state present
          exasol.exasol.exasol_schema:
            name: "{{ check_mode_schema }}"
            state: present
          check_mode: true
          register: schema_check_create

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_check_create }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.check_mode_schema,
        state="present",
        exists=True,
        executed_queries=[_create_schema_query(context.check_mode_schema)],
    )
    assert _schema_count(context.login_vars, context.check_mode_schema) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-check-mode-drop")
def test_exasol_schema_check_mode_drop(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Check mode predicts drop."""
    playbook = """
    - name: Check mode predicts drop
      block:
        - name: When exasol_schema runs in check mode with state absent
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
          check_mode: true
          register: schema_check_drop

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_check_drop }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        state="absent",
        exists=False,
        executed_queries=[_drop_schema_query(context.test_schema)],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-check-mode-drop-cascade")
def test_exasol_schema_check_mode_drop_cascade(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Check mode predicts cascade drop."""
    playbook = """
    - name: Check mode predicts cascade drop
      block:
        - name: When exasol_schema predicts a cascade drop in check mode
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
            cascade: true
          check_mode: true
          register: schema_check_drop_cascade

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_check_drop_cascade }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema, with_table=True)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        state="absent",
        exists=False,
        executed_queries=[_drop_schema_query(context.test_schema, cascade=True)],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-drop-existing-schema")
def test_exasol_schema_drop_existing_schema(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Drop existing empty schema."""
    playbook = """
    - name: Drop existing empty schema
      block:
        - name: When exasol_schema runs with state absent
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
          register: schema_drop

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_drop }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        state="absent",
        exists=False,
        executed_queries=[_drop_schema_query(context.test_schema)],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-drop-existing-schema-cascade")
def test_exasol_schema_drop_existing_schema_cascade(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Drop existing non-empty schema using cascade."""
    playbook = """
    - name: Drop existing schema using cascade
      block:
        - name: When exasol_schema runs with state absent and cascade
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
            cascade: true
          register: schema_drop_cascade

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_drop_cascade }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema, with_table=True)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        state="absent",
        exists=False,
        executed_queries=[_drop_schema_query(context.test_schema, cascade=True)],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-drop-missing-schema")
def test_exasol_schema_drop_missing_schema(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    """Scenario: Drop missing schema."""
    playbook = """
    - name: Drop missing schema
      block:
        - name: When exasol_schema runs with state absent
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
          register: schema_drop_missing

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_drop_missing }}"
            cacheable: true
    """
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    _assert_schema_module_result(
        result["module_result"],
        changed=False,
        schema=context.test_schema,
        state="absent",
        exists=False,
        executed_queries=[],
    )
    assert _schema_count(context.login_vars, context.test_schema) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-create-with-owner")
def test_exasol_schema_create_with_owner(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _execute_sql(context.login_vars, f'CREATE ROLE "{context.test_role}"')
    playbook = """
    - name: Create schema with owner
      block:
        - name: Manage schema owner
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            owner: "{{ test_role }}"
          register: schema_result
        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_result }}"
            cacheable: true
    """

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    assert result["module_result"]["executed_queries"] == [
        _create_schema_query(context.test_schema),
        f'ALTER SCHEMA "{context.test_schema}" CHANGE OWNER "{context.test_role}"',
    ]
    assert (
        _schema_value(context.login_vars, context.test_schema, "SCHEMA_OWNER")
        == context.test_role
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-owner-idempotent")
def test_exasol_schema_owner_idempotent(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _execute_sql(context.login_vars, f'CREATE ROLE "{context.test_role}"')
    _create_schema(context.login_vars, context.test_schema)
    _execute_sql(
        context.login_vars,
        f'ALTER SCHEMA "{context.test_schema}" CHANGE OWNER "{context.test_role}"',
    )
    playbook = """
    - name: Keep matching schema owner
      block:
        - name: Manage schema owner
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            owner: "{{ test_role }}"
          register: schema_result
        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_result }}"
            cacheable: true
    """

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    assert result["module_result"]["changed"] is False
    assert result["module_result"]["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-set-comment")
def test_exasol_schema_set_comment(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)
    playbook = """
    - name: Set schema comment
      block:
        - name: Manage schema comment
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            comment: Sales reporting schema
          register: schema_result
        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_result }}"
            cacheable: true
    """

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    assert result["module_result"]["changed"] is True
    assert (
        _schema_value(context.login_vars, context.test_schema, "SCHEMA_COMMENT")
        == "Sales reporting schema"
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-rename")
def test_exasol_schema_rename(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)
    playbook = """
    - name: Rename schema
      block:
        - name: Manage schema name
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            new_name: "{{ check_mode_schema }}"
          register: schema_result
        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_result }}"
            cacheable: true
    """

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    assert result["module_result"]["schema"] == context.check_mode_schema
    assert _schema_count(context.login_vars, context.test_schema) == 0
    assert _schema_count(context.login_vars, context.check_mode_schema) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-raw-size-limit-check-mode")
def test_exasol_schema_raw_size_limit_check_mode(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    scenario_id: str,
) -> None:
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)
    _execute_sql(
        context.login_vars,
        f'ALTER SCHEMA "{context.test_schema}" SET RAW_SIZE_LIMIT = 1024',
    )
    playbook = """
    - name: Predict schema quota change
      block:
        - name: Manage schema quota in check mode
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            raw_size_limit: 2048
          check_mode: true
          register: schema_result
        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_result }}"
            cacheable: true
    """

    result = _when_schema_scenario_runs(context, scenario_id, playbook)

    assert result["module_result"]["changed"] is True
    assert _raw_size_limit(context.login_vars, context.test_schema) == 1024


def _when_schema_scenario_runs(
    context: AcceptanceContext,
    scenario_id: str,
    playbook: str,
) -> dict[str, Any]:
    return when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )


def _create_schema(
    login_vars: dict[str, object],
    schema_name: str,
    *,
    with_table: bool = False,
) -> None:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")
    connection = connect_to_exasol(login_vars)
    try:
        connection.execute(f"CREATE SCHEMA {quoted_schema}")
        if with_table:
            connection.execute(f"CREATE TABLE {quoted_schema}.TEST_TABLE (ID INT)")
    finally:
        connection.close()


def _execute_sql(login_vars: dict[str, object], query: str) -> None:
    connection = connect_to_exasol(login_vars)
    try:
        connection.execute(query)
    finally:
        connection.close()


def _schema_count(login_vars: dict[str, object], schema_name: str) -> int:
    return len(_stored_schema_names(login_vars, schema_name))


def _stored_schema_names(login_vars: dict[str, object], schema_name: str) -> list[str]:
    normalized_schema_name = validate_schema_name(schema_name)
    schema_name_literal = common_query.quote_sql_string_literal(normalized_schema_name)
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(
            "SELECT SCHEMA_NAME FROM EXA_SCHEMAS "
            f"WHERE UPPER(SCHEMA_NAME) = UPPER({schema_name_literal})"
        ).fetchall()
    finally:
        connection.close()
    return [str(_row_value(row, "SCHEMA_NAME", 0)) for row in rows]


def _schema_value(
    login_vars: dict[str, object], schema_name: str, column: str
) -> object:
    schema_literal = common_query.quote_sql_string_literal(schema_name)
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(
            f"SELECT {column} FROM EXA_SCHEMAS WHERE SCHEMA_NAME = {schema_literal}"
        ).fetchall()
    finally:
        connection.close()
    return _row_value(rows[0], column, 0)


def _raw_size_limit(login_vars: dict[str, object], schema_name: str) -> int | None:
    schema_literal = common_query.quote_sql_string_literal(schema_name)
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(
            "SELECT RAW_OBJECT_SIZE_LIMIT FROM EXA_ALL_OBJECT_SIZES "
            f"WHERE OBJECT_TYPE = 'SCHEMA' AND OBJECT_NAME = {schema_literal}"
        ).fetchall()
    finally:
        connection.close()
    value = _row_value(rows[0], "RAW_OBJECT_SIZE_LIMIT", 0)
    return None if value is None else int(value)


def _assert_schema_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    schema: str,
    state: str,
    exists: bool,
    executed_queries: list[str],
) -> None:
    assert result["changed"] is changed
    assert result["failed"] is False
    assert result["schema"] == schema
    assert result["state"] == state
    assert result["exists"] is exists
    assert result["executed_queries"] == executed_queries


def _create_schema_query(schema_name: str) -> str:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")
    return f"CREATE SCHEMA {quoted_schema}"


def _drop_schema_query(schema_name: str, *, cascade: bool = False) -> str:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")
    suffix = " CASCADE" if cascade else ""
    return f"DROP SCHEMA {quoted_schema}{suffix}"


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]
    return row[index]
