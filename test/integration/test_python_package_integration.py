"""Pure Python backend integration tests for the runtime package."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from exasol.ansible_modules import (
    exasol_query,
    exasol_role,
    exasol_user,
)


@pytest.mark.integration
@pytest.mark.slow
def test_python_package_query_runtime_executes_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the query runtime can execute read-only and mutating SQL directly."""
    schema_name = _unique_name("ANSIBLE_PYTHON_SCHEMA")

    with exasol_query.connect_to_exasol(
        exasol_login_vars,
        module_name="python package integration test",
    ) as connection:
        try:
            create_result = exasol_query.execute_queries(
                connection,
                f'CREATE SCHEMA "{schema_name}"',
            )
            read_result = exasol_query.execute_queries(
                connection,
                "SELECT COUNT(*) AS SCHEMA_COUNT "
                f"FROM EXA_ALL_SCHEMAS WHERE SCHEMA_NAME = '{schema_name}'",
            )

            assert create_result["changed"] is True
            assert create_result["executed_queries"] == [
                f'CREATE SCHEMA "{schema_name}"'
            ]
            assert read_result["changed"] is False
            assert _row_int(read_result["query_result"][0], "SCHEMA_COUNT") == 1
        finally:
            exasol_query.execute_queries(
                connection,
                f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE',
            )


@pytest.mark.integration
@pytest.mark.slow
def test_python_package_user_runtime_manages_user_lifecycle(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the user runtime manages repeated runs and password updates."""
    user_name = _unique_name("ANSIBLE_PYTHON_USER")
    initial_password = f"Initial_{uuid.uuid4().hex}"
    rotated_password = f"Rotated_{uuid.uuid4().hex}"

    with exasol_query.connect_to_exasol(
        exasol_login_vars,
        module_name="python package integration test",
    ) as connection:
        create_result = exasol_user.ensure_user(
            connection,
            {"name": user_name, "password": initial_password},
        )
        unchanged_result = exasol_user.ensure_user(
            connection,
            {
                "name": user_name,
                "password": initial_password,
                "update_password": "on_create",
            },
        )
        update_result = exasol_user.ensure_user(
            connection,
            {
                "name": user_name,
                "password": rotated_password,
                "update_password": "always",
            },
        )
        drop_result = exasol_user.ensure_user(
            connection,
            {"name": user_name, "state": "absent", "cascade": True},
        )
        count_result = exasol_query.execute_queries(
            connection,
            "SELECT COUNT(*) AS USER_COUNT "
            f"FROM EXA_ALL_USERS WHERE USER_NAME = '{user_name}'",
        )

    assert create_result["changed"] is True
    assert create_result["user"] == user_name
    assert create_result["exists"] is True
    assert create_result["executed_queries"] == [
        f'CREATE USER "{user_name}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{user_name}"',
    ]
    assert unchanged_result["changed"] is False
    assert unchanged_result["executed_queries"] == []
    assert update_result["changed"] is True
    assert update_result["executed_queries"] == [
        f'ALTER USER "{user_name}" IDENTIFIED BY "********"'
    ]
    assert drop_result["changed"] is True
    assert drop_result["exists"] is False
    assert drop_result["executed_queries"] == [f'DROP USER "{user_name}" CASCADE']
    assert _row_int(count_result["query_result"][0], "USER_COUNT") == 0


@pytest.mark.integration
@pytest.mark.slow
def test_python_package_role_runtime_manages_role_lifecycle(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the role runtime manages repeated runs directly against Exasol."""
    role_name = _unique_name("ANSIBLE_PYTHON_ROLE")

    with exasol_query.connect_to_exasol(
        exasol_login_vars,
        module_name="python package integration test",
    ) as connection:
        create_result = exasol_role.ensure_role(connection, {"name": role_name})
        unchanged_result = exasol_role.ensure_role(connection, {"name": role_name})
        drop_result = exasol_role.ensure_role(
            connection,
            {"name": role_name, "state": "absent", "cascade": True},
        )
        count_result = exasol_query.execute_queries(
            connection,
            "SELECT COUNT(*) AS ROLE_COUNT "
            f"FROM EXA_ALL_ROLES WHERE ROLE_NAME = '{role_name}'",
        )

    assert create_result["changed"] is True
    assert create_result["role"] == role_name
    assert create_result["exists"] is True
    assert create_result["executed_queries"] == [f'CREATE ROLE "{role_name}"']
    assert unchanged_result["changed"] is False
    assert unchanged_result["executed_queries"] == []
    assert drop_result["changed"] is True
    assert drop_result["exists"] is False
    assert drop_result["executed_queries"] == [f'DROP ROLE "{role_name}" CASCADE']
    assert _row_int(count_result["query_result"][0], "ROLE_COUNT") == 0


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex.upper()}"


def _row_int(row: object, key: str) -> int:
    value: Any
    if isinstance(row, dict):
        value = row[key]
    else:
        value = row[0]
    return int(value)
