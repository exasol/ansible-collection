"""Pure Python backend integration tests for the role runtime."""

from __future__ import annotations

import pytest
from python_package_integration_common import (
    catalog_count,
    execute_sql,
    unique_name,
)

from exasol.ansible_modules import (
    exasol_role,
)


@pytest.mark.integration
@pytest.mark.slow
def test_role_runtime_creates_missing_role(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the role runtime creates a missing role."""
    role_name = unique_name("ANSIBLE_PYTHON_ROLE")

    create_result = exasol_role.run_role(
        {
            **exasol_login_vars,
            "name": role_name,
        }
    )
    role_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_ROLES",
        column="ROLE_NAME",
        object_name=role_name,
        result_key="ROLE_COUNT",
    )

    assert create_result["changed"] is True
    assert create_result["role"] == role_name
    assert create_result["exists"] is True
    assert create_result["executed_queries"] == [f'CREATE ROLE "{role_name}"']
    assert role_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_role_runtime_leaves_existing_role_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the role runtime reports no changes for an existing role."""
    role_name = unique_name("ANSIBLE_PYTHON_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{role_name}"')

    unchanged_result = exasol_role.run_role(
        {
            **exasol_login_vars,
            "name": role_name,
        }
    )
    role_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_ROLES",
        column="ROLE_NAME",
        object_name=role_name,
        result_key="ROLE_COUNT",
    )

    assert unchanged_result["changed"] is False
    assert unchanged_result["role"] == role_name
    assert unchanged_result["exists"] is True
    assert unchanged_result["executed_queries"] == []
    assert role_count == 1


@pytest.mark.integration
@pytest.mark.slow
def test_role_runtime_drops_existing_role(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the role runtime drops an existing role."""
    role_name = unique_name("ANSIBLE_PYTHON_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{role_name}"')

    drop_result = exasol_role.run_role(
        {
            **exasol_login_vars,
            "name": role_name,
            "state": "absent",
            "cascade": True,
        }
    )
    role_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_ROLES",
        column="ROLE_NAME",
        object_name=role_name,
        result_key="ROLE_COUNT",
    )

    assert drop_result["changed"] is True
    assert drop_result["role"] == role_name
    assert drop_result["exists"] is False
    assert drop_result["executed_queries"] == [f'DROP ROLE "{role_name}" CASCADE']
    assert role_count == 0


@pytest.mark.integration
@pytest.mark.slow
def test_role_runtime_check_mode_predicts_create_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify role check mode reports creation without persisting the role."""
    role_name = unique_name("ANSIBLE_PYTHON_ROLE")

    predicted_result = exasol_role.run_role(
        {
            **exasol_login_vars,
            "name": role_name,
        },
        check_mode=True,
    )
    role_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_ROLES",
        column="ROLE_NAME",
        object_name=role_name,
        result_key="ROLE_COUNT",
    )

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is True
    assert predicted_result["executed_queries"] == [f'CREATE ROLE "{role_name}"']
    assert role_count == 0


@pytest.mark.integration
@pytest.mark.slow
def test_role_runtime_check_mode_predicts_drop_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify role check mode reports drop without removing the role."""
    role_name = unique_name("ANSIBLE_PYTHON_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{role_name}"')

    predicted_result = exasol_role.run_role(
        {
            **exasol_login_vars,
            "name": role_name,
            "state": "absent",
            "cascade": True,
        },
        check_mode=True,
    )
    role_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_ROLES",
        column="ROLE_NAME",
        object_name=role_name,
        result_key="ROLE_COUNT",
    )

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is False
    assert predicted_result["executed_queries"] == [f'DROP ROLE "{role_name}" CASCADE']
    assert role_count == 1
