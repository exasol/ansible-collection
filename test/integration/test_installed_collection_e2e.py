"""Installed-artifact E2E smoke tests for collection modules."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from acceptance_common.acceptance_test_common import (
    connect_to_exasol,
    given_acceptance_context,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)
from conftest import InstalledCollectionEnvironment

from exasol.ansible_modules.common_identifier_validation import quote_identifier


@pytest.mark.integration
@pytest.mark.slow
def test_installed_exasol_query_smoke_succeeds(
    tmp_path: Path,
    installed_collection_environment: InstalledCollectionEnvironment,
    exasol_login_vars: dict[str, object],
) -> None:
    """Run a read-only query through the built collection and installed runtime."""
    workspace = _installed_runner_workspace(tmp_path, installed_collection_environment)
    context = given_acceptance_context(
        workspace,
        exasol_login_vars,
        python_interpreter=installed_collection_environment.python_executable,
    )

    result = when_module_scenario_runs(
        context,
        "exasol_query",
        "installed-exasol-query-smoke",
        scenario_playbook="""
        - name: Read database version metadata through installed artifacts
          block:
            - name: Query EXA_METADATA
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
        """,
    )

    module_result = result["module_result"]
    assert module_result["changed"] is False
    assert module_result["query_result"]
    assert module_result["query_result"][0]["PARAM_VALUE"]
    assert module_result["executed_queries"] == [
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion'"
    ]


@pytest.mark.integration
@pytest.mark.slow
def test_installed_exasol_user_smoke_succeeds(
    tmp_path: Path,
    installed_collection_environment: InstalledCollectionEnvironment,
    exasol_login_vars: dict[str, object],
) -> None:
    """Create a user through the built collection and installed runtime."""
    workspace = _installed_runner_workspace(tmp_path, installed_collection_environment)
    context = given_acceptance_context(
        workspace,
        exasol_login_vars,
        python_interpreter=installed_collection_environment.python_executable,
    )

    result = when_module_scenario_runs(
        context,
        "exasol_user",
        "installed-exasol-user-smoke",
        scenario_playbook="""
        - name: Create a user through installed artifacts
          block:
            - name: Ensure the user is absent before the smoke run
              exasol.exasol.exasol_user:
                name: "{{ test_user }}"
                state: absent
                cascade: true

            - name: Create the user
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
        """,
    )

    module_result = result["module_result"]
    assert module_result["changed"] is True
    assert module_result["user"] == context.test_user
    assert module_result["exists"] is True
    assert len(module_result["executed_queries"]) == 2
    _assert_exasol_object_count(
        exasol_login_vars,
        f"SELECT COUNT(*) AS USER_COUNT FROM EXA_ALL_USERS WHERE USER_NAME = '{context.test_user}'",
        "USER_COUNT",
        1,
    )
    then_secret_is_not_exposed(result, context.test_user_password)


@pytest.mark.integration
@pytest.mark.slow
def test_installed_exasol_role_smoke_succeeds(
    tmp_path: Path,
    installed_collection_environment: InstalledCollectionEnvironment,
    exasol_login_vars: dict[str, object],
) -> None:
    """Create a role through the built collection and installed runtime."""
    workspace = _installed_runner_workspace(tmp_path, installed_collection_environment)
    context = given_acceptance_context(
        workspace,
        exasol_login_vars,
        python_interpreter=installed_collection_environment.python_executable,
    )

    result = when_module_scenario_runs(
        context,
        "exasol_role",
        "installed-exasol-role-smoke",
        scenario_playbook="""
        - name: Create a role through installed artifacts
          block:
            - name: Ensure the role is absent before the smoke run
              exasol.exasol.exasol_role:
                name: "{{ test_role }}"
                state: absent
                cascade: true

            - name: Create the role
              exasol.exasol.exasol_role:
                name: "{{ test_role }}"
              register: exasol_role_create

            - name: Store scenario result
              ansible.builtin.set_fact:
                acceptance_result:
                  scenario_id: "{{ acceptance_scenario_id }}"
                  module_result: "{{ exasol_role_create }}"
                cacheable: true
        """,
    )

    module_result = result["module_result"]
    assert module_result["changed"] is True
    assert module_result["role"] == context.test_role
    assert module_result["state"] == "present"
    assert module_result["exists"] is True
    assert module_result["executed_queries"] == [
        f"CREATE ROLE {quote_identifier(context.test_role)}"
    ]
    _assert_exasol_object_count(
        exasol_login_vars,
        f"SELECT COUNT(*) AS ROLE_COUNT FROM EXA_ALL_ROLES WHERE ROLE_NAME = '{context.test_role}'",
        "ROLE_COUNT",
        1,
    )


def _installed_runner_workspace(
    tmp_path: Path,
    installed_collection_environment: InstalledCollectionEnvironment,
) -> SimpleNamespace:
    private_data_dir = tmp_path / "runner"
    project_dir = private_data_dir / "project"
    env_dir = private_data_dir / "env"
    project_dir.mkdir(parents=True)
    env_dir.mkdir()
    (private_data_dir / "inventory").write_text(
        "localhost ansible_connection=local\n",
        encoding="utf-8",
    )
    (env_dir / "envvars").write_text(
        yaml.safe_dump(installed_collection_environment.env),
        encoding="utf-8",
    )
    return SimpleNamespace(
        private_data_dir=private_data_dir,
        project_dir=project_dir,
    )


def _assert_exasol_object_count(
    login_vars: dict[str, object],
    query: str,
    field_name: str,
    expected: int,
) -> None:
    connection = connect_to_exasol(login_vars)
    try:
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()
    assert int(_row_value(rows[0], field_name, 0)) == expected


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]

    return row[index]
