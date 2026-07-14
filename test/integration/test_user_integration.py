"""Pure Python backend integration tests for the user runtime."""

from __future__ import annotations

import uuid
from test.integration.integration_common import (
    catalog_count,
    execute_sql,
    unique_name,
)

import pytest

from exasol.ansible_modules import (
    exasol_user,
)


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_creates_missing_user(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the user runtime creates a missing user."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    initial_password = f"Initial_{uuid.uuid4().hex}"

    create_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "password": initial_password,
        }
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert create_result["changed"] is True
    assert create_result["user"] == user_name
    assert create_result["exists"] is True
    assert create_result["executed_queries"] == [
        f'CREATE USER "{user_name}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{user_name}"',
    ]
    assert user_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_leaves_existing_user_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the user runtime reports no changes for an existing user."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    initial_password = f"Initial_{uuid.uuid4().hex}"

    execute_sql(
        exasol_login_vars,
        f'CREATE USER "{user_name}" IDENTIFIED BY "{initial_password}"',
    )

    unchanged_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "password": initial_password,
            "update_password": "on_create",
        }
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert unchanged_result["changed"] is False
    assert unchanged_result["user"] == user_name
    assert unchanged_result["exists"] is True
    assert unchanged_result["executed_queries"] == []
    assert user_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_updates_existing_user_password(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the user runtime updates an existing user's password."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    initial_password = f"Initial_{uuid.uuid4().hex}"
    rotated_password = f"Rotated_{uuid.uuid4().hex}"

    execute_sql(
        exasol_login_vars,
        f'CREATE USER "{user_name}" IDENTIFIED BY "{initial_password}"',
    )

    update_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "password": rotated_password,
            "update_password": "always",
        }
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert update_result["changed"] is True
    assert update_result["user"] == user_name
    assert update_result["exists"] is True
    assert update_result["executed_queries"] == [
        f'ALTER USER "{user_name}" IDENTIFIED BY "********"'
    ]
    assert user_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_drops_existing_user(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the user runtime drops an existing user."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    initial_password = f"Initial_{uuid.uuid4().hex}"

    execute_sql(
        exasol_login_vars,
        f'CREATE USER "{user_name}" IDENTIFIED BY "{initial_password}"',
    )

    drop_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "state": "absent",
            "cascade": True,
        }
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert drop_result["changed"] is True
    assert drop_result["user"] == user_name
    assert drop_result["exists"] is False
    assert drop_result["executed_queries"] == [f'DROP USER "{user_name}" CASCADE']
    assert user_count == 0


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_check_mode_predicts_create_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify user check mode reports creation without persisting the user."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    password = f"Initial_{uuid.uuid4().hex}"

    predicted_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "password": password,
        },
        check_mode=True,
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is True
    assert predicted_result["executed_queries"] == [
        f'CREATE USER "{user_name}" IDENTIFIED BY "********"',
        f'GRANT CREATE SESSION TO "{user_name}"',
    ]
    assert user_count == 0


@pytest.mark.integration
@pytest.mark.slow
def test_user_runtime_check_mode_predicts_drop_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify user check mode reports drop without removing the user."""
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    password = f"Initial_{uuid.uuid4().hex}"

    execute_sql(
        exasol_login_vars,
        f'CREATE USER "{user_name}" IDENTIFIED BY "{password}"',
    )

    predicted_result = exasol_user.run_user(
        {
            **exasol_login_vars,
            "name": user_name,
            "state": "absent",
            "cascade": True,
        },
        check_mode=True,
    )
    user_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_USERS",
        column="USER_NAME",
        object_name=user_name,
        result_key="USER_COUNT",
    )

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is False
    assert predicted_result["executed_queries"] == [f'DROP USER "{user_name}" CASCADE']
    assert user_count == 1
