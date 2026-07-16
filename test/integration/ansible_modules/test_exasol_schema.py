"""Pure Python backend integration tests for the schema runtime."""

from __future__ import annotations

import pytest
from ansible_modules.common_helpers import (
    catalog_count,
    execute_sql,
    unique_name,
)

from exasol.ansible_modules import exasol_schema


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-create-missing-schema")
def test_schema_runtime_creates_missing_schema(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the schema runtime creates a missing schema."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")

    create_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
        }
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert create_result["changed"] is True
    assert create_result["schema"] == schema_name
    assert create_result["exists"] is True
    assert create_result["executed_queries"] == [f'CREATE SCHEMA "{schema_name}"']
    assert schema_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-leave-existing-schema-unchanged")
def test_schema_runtime_leaves_existing_schema_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the schema runtime reports no changes for an existing schema."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    unchanged_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
        }
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert unchanged_result["changed"] is False
    assert unchanged_result["schema"] == schema_name
    assert unchanged_result["exists"] is True
    assert unchanged_result["executed_queries"] == []
    assert schema_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-drop-existing-schema")
def test_schema_runtime_drops_existing_schema(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the schema runtime drops an existing schema."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    drop_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
            "state": "absent",
        }
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert drop_result["changed"] is True
    assert drop_result["schema"] == schema_name
    assert drop_result["exists"] is False
    assert drop_result["executed_queries"] == [f'DROP SCHEMA "{schema_name}"']
    assert schema_count == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-check-mode-predicts-create-without-writing")
def test_schema_runtime_check_mode_predicts_create_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify schema check mode predicts creation without persisting it."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")

    predicted_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
        },
        check_mode=True,
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is True
    assert predicted_result["executed_queries"] == [f'CREATE SCHEMA "{schema_name}"']
    assert schema_count == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-schema-check-mode-predicts-no-action-when-schema-exists"
)
def test_schema_runtime_check_mode_predicts_no_action_when_schema_exists(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify schema check mode reports no action for an existing schema."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    unchanged_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
        },
        check_mode=True,
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert unchanged_result["changed"] is False
    assert unchanged_result["schema"] == schema_name
    assert unchanged_result["exists"] is True
    assert unchanged_result["executed_queries"] == []
    assert schema_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-check-mode-predicts-drop-without-writing")
def test_schema_runtime_check_mode_predicts_drop_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify schema check mode predicts a cascade drop without persisting it."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    predicted_result = exasol_schema.run_schema(
        {
            **exasol_login_vars,
            "name": schema_name,
            "state": "absent",
            "cascade": True,
        },
        check_mode=True,
    )
    schema_count = _schema_count(exasol_login_vars, schema_name)

    assert predicted_result["changed"] is True
    assert predicted_result["exists"] is False
    assert predicted_result["executed_queries"] == [
        f'DROP SCHEMA "{schema_name}" CASCADE'
    ]
    assert schema_count == 1


def _schema_count(login_vars: dict[str, object], schema_name: str) -> int:
    return catalog_count(
        login_vars,
        table="EXA_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )
