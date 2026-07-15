"""Pure Python backend integration tests for the init orchestration runtime."""

from __future__ import annotations

import uuid

import pytest
from integration_common import (
    catalog_count,
    query_row_count,
    unique_name,
)

from exasol.ansible_modules import exasol_init


@pytest.mark.integration
@pytest.mark.slow
def test_init_runtime_creates_full_environment(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a full run creates roles, users, grants, schemas, and scripts in order."""
    scenario_id = "exasol-init-create-full-environment"
    role_name = unique_name("ANSIBLE_PYTHON_INIT_ROLE")
    user_name = unique_name("ANSIBLE_PYTHON_INIT_USER")
    schema_name = unique_name("ANSIBLE_PYTHON_INIT_SCHEMA")
    password = f"Initial_{uuid.uuid4().hex}"

    create_result = exasol_init.run_init(
        {
            **exasol_login_vars,
            "roles": [{"name": role_name}],
            "users": [{"name": user_name, "password": password}],
            "role_grants": [{"role": role_name, "user": user_name}],
            "schemas": [{"name": schema_name, "owner": user_name}],
            "grants": [
                {"schema": schema_name, "privilege": "SELECT", "grantee": role_name}
            ],
            "scripts": [f"CREATE TABLE {schema_name}.EVENTS (ID INT)"],
        }
    )

    assert create_result["changed"] is True
    assert create_result["executed_queries"] == [
        f'CREATE ROLE "{role_name}"',
        f'CREATE USER "{user_name}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{user_name}"',
        f'GRANT "{role_name}" TO "{user_name}"',
        f'CREATE SCHEMA "{schema_name}"',
        f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{user_name}"',
        f'GRANT SELECT ON SCHEMA "{schema_name}" TO "{role_name}"',
        f"CREATE TABLE {schema_name}.EVENTS (ID INT)",
    ]

    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_ROLES",
            column="ROLE_NAME",
            object_name=role_name,
            result_key="ROLE_COUNT",
        )
        == 1
    )
    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_USERS",
            column="USER_NAME",
            object_name=user_name,
            result_key="USER_COUNT",
        )
        == 1
    )
    assert (
        query_row_count(
            exasol_login_vars,
            "SELECT COUNT(*) AS ROW_COUNT FROM EXA_DBA_ROLE_GRANTS "
            f"WHERE GRANTEE = '{user_name}' AND GRANTED_ROLE = '{role_name}'",
        )
        == 1
    )
    assert (
        query_row_count(
            exasol_login_vars,
            "SELECT COUNT(*) AS ROW_COUNT FROM EXA_DBA_OBJ_PRIVS "
            f"WHERE OBJECT_NAME = '{schema_name}' AND GRANTEE = '{role_name}' "
            "AND PRIVILEGE = 'SELECT'",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
def test_init_runtime_leaves_existing_environment_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify re-running an already-initialized environment makes no changes."""
    scenario_id = "exasol-init-leave-existing-environment-unchanged"
    role_name = unique_name("ANSIBLE_PYTHON_INIT_ROLE")
    user_name = unique_name("ANSIBLE_PYTHON_INIT_USER")
    schema_name = unique_name("ANSIBLE_PYTHON_INIT_SCHEMA")
    password = f"Initial_{uuid.uuid4().hex}"

    params = {
        **exasol_login_vars,
        "roles": [{"name": role_name}],
        "users": [{"name": user_name, "password": password}],
        "role_grants": [{"role": role_name, "user": user_name}],
        "schemas": [{"name": schema_name, "owner": user_name}],
        "grants": [
            {"schema": schema_name, "privilege": "SELECT", "grantee": role_name}
        ],
    }
    exasol_init.run_init(params)

    unchanged_result = exasol_init.run_init(
        {
            **params,
            "users": [
                {**params["users"][0], "update_password": "on_create"}  # type: ignore[index]
            ],
        }
    )

    assert unchanged_result["changed"] is False
    assert unchanged_result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
def test_init_runtime_check_mode_predicts_plan_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode predicts the full plan without touching the database."""
    scenario_id = "exasol-init-check-mode-predicts-plan-without-writing"
    role_name = unique_name("ANSIBLE_PYTHON_INIT_ROLE")
    user_name = unique_name("ANSIBLE_PYTHON_INIT_USER")
    schema_name = unique_name("ANSIBLE_PYTHON_INIT_SCHEMA")
    password = f"Check_{uuid.uuid4().hex}"

    predicted_result = exasol_init.run_init(
        {
            **exasol_login_vars,
            "roles": [{"name": role_name}],
            "users": [{"name": user_name, "password": password}],
            "role_grants": [{"role": role_name, "user": user_name}],
            "schemas": [{"name": schema_name, "owner": user_name}],
            "grants": [
                {"schema": schema_name, "privilege": "SELECT", "grantee": role_name}
            ],
            "scripts": [f"CREATE TABLE {schema_name}.T (ID INT)"],
        },
        check_mode=True,
    )

    assert predicted_result["changed"] is True
    assert len(predicted_result["executed_queries"]) == 8
    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_ROLES",
            column="ROLE_NAME",
            object_name=role_name,
            result_key="ROLE_COUNT",
        )
        == 0
    )
    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_USERS",
            column="USER_NAME",
            object_name=user_name,
            result_key="USER_COUNT",
        )
        == 0
    )
    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_SCHEMAS",
            column="SCHEMA_NAME",
            object_name=schema_name,
            result_key="SCHEMA_COUNT",
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
def test_init_runtime_drops_environment_with_cascade(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a teardown request drops dependents before dependencies."""
    scenario_id = "exasol-init-drop-environment-with-cascade"
    role_name = unique_name("ANSIBLE_PYTHON_INIT_ROLE")
    user_name = unique_name("ANSIBLE_PYTHON_INIT_USER")
    schema_name = unique_name("ANSIBLE_PYTHON_INIT_SCHEMA")
    password = f"Initial_{uuid.uuid4().hex}"

    exasol_init.run_init(
        {
            **exasol_login_vars,
            "roles": [{"name": role_name}],
            "users": [{"name": user_name, "password": password}],
            "role_grants": [{"role": role_name, "user": user_name}],
            "schemas": [{"name": schema_name, "owner": user_name}],
            "grants": [
                {"schema": schema_name, "privilege": "SELECT", "grantee": role_name}
            ],
        }
    )

    drop_result = exasol_init.run_init(
        {
            **exasol_login_vars,
            "grants": [
                {
                    "schema": schema_name,
                    "privilege": "SELECT",
                    "grantee": role_name,
                    "state": "absent",
                }
            ],
            "role_grants": [{"role": role_name, "user": user_name, "state": "absent"}],
            "schemas": [{"name": schema_name, "state": "absent", "cascade": True}],
            "users": [{"name": user_name, "state": "absent", "cascade": True}],
            "roles": [{"name": role_name, "state": "absent", "cascade": True}],
        }
    )

    assert drop_result["changed"] is True
    assert drop_result["executed_queries"] == [
        f'REVOKE SELECT ON SCHEMA "{schema_name}" FROM "{role_name}"',
        f'REVOKE "{role_name}" FROM "{user_name}"',
        f'DROP SCHEMA "{schema_name}" CASCADE',
        f'DROP USER "{user_name}" CASCADE',
        f'DROP ROLE "{role_name}" CASCADE',
    ]
    for table, column, object_name, result_key in (
        ("EXA_ALL_ROLES", "ROLE_NAME", role_name, "ROLE_COUNT"),
        ("EXA_ALL_USERS", "USER_NAME", user_name, "USER_COUNT"),
        ("EXA_ALL_SCHEMAS", "SCHEMA_NAME", schema_name, "SCHEMA_COUNT"),
    ):
        assert (
            catalog_count(
                exasol_login_vars,
                table=table,
                column=column,
                object_name=object_name,
                result_key=result_key,
            )
            == 0
        )


@pytest.mark.integration
@pytest.mark.slow
def test_init_runtime_executes_scripts_after_grants(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify init scripts run last, after the schema grant has been applied."""
    scenario_id = "exasol-init-execute-scripts-after-grants"
    role_name = unique_name("ANSIBLE_PYTHON_INIT_ROLE")
    schema_name = unique_name("ANSIBLE_PYTHON_INIT_SCHEMA")

    result = exasol_init.run_init(
        {
            **exasol_login_vars,
            "roles": [{"name": role_name}],
            "schemas": [{"name": schema_name}],
            "grants": [
                {"schema": schema_name, "privilege": "SELECT", "grantee": role_name}
            ],
            "scripts": [f"CREATE TABLE {schema_name}.ARTICLES (ID INT)"],
        }
    )

    assert result["changed"] is True
    assert (
        result["executed_queries"][-1]
        == f"CREATE TABLE {schema_name}.ARTICLES (ID INT)"
    )
    assert (
        catalog_count(
            exasol_login_vars,
            table="EXA_ALL_SCHEMAS",
            column="SCHEMA_NAME",
            object_name=schema_name,
            result_key="SCHEMA_COUNT",
        )
        == 1
    )
