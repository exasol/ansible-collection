"""Playbook-backed tests for exasol-schema feature scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from acceptance_common.acceptance_test_common import (
    connect_to_exasol,
    given_acceptance_context,
    when_module_scenario_runs,
)

from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
)

MODULE_NAME = "exasol_schema"


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_create_missing_schema(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-create-missing-schema"

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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.test_schema,
        exists=True,
        executed_queries_len=1,
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_preserves_exact_identifier(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-preserves-exact-identifier"

    playbook = """
    - name: Preserve exact schema identifier
      block:
        - name: When exasol_schema runs with exact identifier
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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        schema=context.exact_test_schema,
        exists=True,
        executed_queries_len=1,
    )

    assert (
        result["module_result"]["executed_queries"][0]
        == f'CREATE SCHEMA "{context.exact_test_schema}"'
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_apply_unchanged(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-apply-unchanged"

    playbook = """
    - name: Applying identical schema state results in no changes
      block:
        - name: When exasol_schema runs again
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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"], changed=False, exists=True, executed_queries_len=0
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_apply_unchanged_with_different_case_spelling(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-apply-unchanged-with-different-case-spelling"

    playbook = """
    - name: Case insensitive schema lookup
      block:
        - name: When schema is applied with different case
          exasol.exasol.exasol_schema:
            name: "{{ exact_test_schema | lower }}"
            state: present
          register: schema_case_variant

        - name: Read schema metadata
          exasol.exasol.exasol_query:
            query: >-
              SELECT SCHEMA_NAME
              FROM EXA_SCHEMAS
              WHERE UPPER(SCHEMA_NAME) = UPPER(:schema_name)
            named_args:
              schema_name: "{{ exact_test_schema }}"
          register: schema_metadata

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ schema_case_variant }}"
              metadata_result: "{{ schema_metadata }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.exact_test_schema)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=False,
        schema=context.exact_test_schema.lower(),
        exists=True,
        executed_queries_len=0,
    )

    assert result["metadata_result"]["query_result"] == [
        {"SCHEMA_NAME": context.exact_test_schema}
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_check_mode_create(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-check-mode-create"

    playbook = """
    - name: Check mode predicts create
      block:
        - name: When schema runs in check mode
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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"], changed=True, exists=True, executed_queries_len=1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_check_mode_drop(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-check-mode-drop"

    playbook = """
    - name: Check mode predicts drop
      block:
        - name: When schema drop is checked
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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"], changed=True, exists=False, executed_queries_len=1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_check_mode_drop_cascade(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-check-mode-drop-cascade"

    playbook = """
    - name: Check mode predicts cascade drop
      block:
        - name: When exasol_schema predicts cascade drop in check mode
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
            cascade: true
          check_mode: true
          register: exasol_schema_check_drop_cascade

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_schema_check_drop_cascade }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema, with_table=True)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        exists=False,
        schema=context.test_schema,
        executed_queries_len=1,
    )

    assert result["module_result"]["executed_queries"] == [
        f'DROP SCHEMA "{context.test_schema}" CASCADE'
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_drop_existing_schema(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-drop-existing-schema"

    playbook = """
    - name: Drop existing empty schema
      block:
        - name: When exasol_schema drops schema
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
          register: exasol_schema_drop

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_schema_drop }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        exists=False,
        schema=context.test_schema,
        executed_queries_len=1,
    )

    assert result["module_result"]["executed_queries"] == [
        f'DROP SCHEMA "{context.test_schema}"'
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_drop_existing_schema_cascade(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-drop-existing-schema-cascade"

    playbook = """
    - name: Drop existing schema using cascade
      block:
        - name: When exasol_schema drops schema with cascade
          exasol.exasol.exasol_schema:
            name: "{{ test_schema }}"
            state: absent
            cascade: true
          register: exasol_schema_drop_cascade

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_schema_drop_cascade }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    _create_schema(context.login_vars, context.test_schema, with_table=True)

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"],
        changed=True,
        exists=False,
        schema=context.test_schema,
        executed_queries_len=1,
    )

    assert result["module_result"]["executed_queries"] == [
        f'DROP SCHEMA "{context.test_schema}" CASCADE'
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_schema_drop_missing_schema(
    ansible_runner_workspace: Any, exasol_login_vars: dict[str, object]
) -> None:
    scenario_id = "exasol-schema-drop-missing-schema"

    playbook = """
    - name: Drop missing schema
      block:
        - name: When schema absent is applied again
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

    result = when_module_scenario_runs(
        context, MODULE_NAME, scenario_id, scenario_playbook=playbook
    )

    _assert_schema_module_result(
        result["module_result"], changed=False, exists=False, executed_queries_len=0
    )


# -----------------------
# helpers
# -----------------------


def _create_schema(
    login_vars: dict[str, object], schema_name: str, *, with_table: bool = False
) -> None:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")
    connection = connect_to_exasol(login_vars)
    try:
        connection.execute(f"CREATE SCHEMA {quoted_schema}")
        if with_table:
            connection.execute(f"CREATE TABLE {quoted_schema}.TEST_TABLE (ID INT)")
    finally:
        connection.close()


def _assert_schema_module_result(
    result: dict[str, Any],
    *,
    changed: bool,
    exists: bool | None = None,
    schema: str | None = None,
    executed_queries_len: int,
) -> None:
    expected_keys = {
        "changed",
        "executed_queries",
        "exists",
        "failed",
        "result_json",
        "schema",
        "state",
    }

    assert set(result) <= expected_keys
    assert result["changed"] is changed
    assert result["failed"] is False

    if exists is not None:
        assert result["exists"] is exists
        assert result["state"] == ("present" if exists else "absent")

    if schema is not None:
        assert result["schema"] == schema
    else:
        assert isinstance(result["schema"], str)

    assert isinstance(result["executed_queries"], list)
    assert len(result["executed_queries"]) == executed_queries_len
