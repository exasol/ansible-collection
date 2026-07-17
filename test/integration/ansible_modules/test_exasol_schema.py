"""Pure Python backend integration tests for the schema runtime."""

from __future__ import annotations

import pyexasol
import pytest
from ansible_modules.common_helpers import (
    catalog_count,
    execute_sql,
    unique_name,
)

from exasol.ansible_modules import (
    common_query,
    exasol_query,
    exasol_schema,
)


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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-create-with-owner")
def test_schema_runtime_creates_schema_with_owner(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    owner = unique_name("ANSIBLE_OWNER_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{owner}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "owner": owner}
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        f'CREATE SCHEMA "{schema_name}"',
        f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{owner}"',
    ]
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER") == owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-owner-does-not-exist")
def test_schema_runtime_rejects_non_existent_owner(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    non_existent_owner = unique_name("ANSIBLE_MISSING_OWNER")

    with pytest.raises(pyexasol.ExaQueryError):
        exasol_schema.run_schema(
            {**exasol_login_vars, "name": schema_name, "owner": non_existent_owner}
        )

    # CREATE SCHEMA and ALTER SCHEMA CHANGE OWNER run as separate autocommitted
    # statements, so CREATE SCHEMA already committed before CHANGE OWNER failed.
    assert _schema_count(exasol_login_vars, schema_name) == 1
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER")
        != non_existent_owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-change-owner")
def test_schema_runtime_changes_owner(exasol_login_vars: dict[str, object]) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    old_owner = unique_name("ANSIBLE_OLD_OWNER")
    new_owner = unique_name("ANSIBLE_NEW_OWNER")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{old_owner}"')
    execute_sql(exasol_login_vars, f'CREATE ROLE "{new_owner}"')
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars,
        f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{old_owner}"',
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "owner": new_owner}
    )

    assert result["executed_queries"] == [
        f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{new_owner}"'
    ]
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER")
        == new_owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-owner-idempotent")
def test_schema_runtime_leaves_matching_owner_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    owner = unique_name("ANSIBLE_OWNER_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{owner}"')
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{owner}"'
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "owner": owner}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER") == owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-owner-check-mode")
def test_schema_runtime_predicts_owner_change_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    owner = unique_name("ANSIBLE_OWNER_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{owner}"')
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    original_owner = _schema_metadata_value(
        exasol_login_vars, schema_name, "SCHEMA_OWNER"
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "owner": owner}, check_mode=True
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{owner}"'
    ]
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER")
        == original_owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-owner-check-mode-idempotent")
def test_schema_runtime_check_mode_predicts_no_owner_change_when_matching(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    owner = unique_name("ANSIBLE_OWNER_ROLE")
    execute_sql(exasol_login_vars, f'CREATE ROLE "{owner}"')
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f'ALTER SCHEMA "{schema_name}" CHANGE OWNER "{owner}"'
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "owner": owner}, check_mode=True
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_OWNER") == owner
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-set-comment")
def test_schema_runtime_sets_comment(exasol_login_vars: dict[str, object]) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    comment = "Sales team's reporting schema"
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "comment": comment}
    )

    assert result["executed_queries"] == [
        f"COMMENT ON SCHEMA \"{schema_name}\" IS 'Sales team''s reporting schema'"
    ]
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_COMMENT")
        == comment
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-clear-comment")
def test_schema_runtime_clears_comment(exasol_login_vars: dict[str, object]) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(exasol_login_vars, f"COMMENT ON SCHEMA \"{schema_name}\" IS 'Old'")

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "comment": ""}
    )

    assert result["executed_queries"] == [f'COMMENT ON SCHEMA "{schema_name}" IS NULL']
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_COMMENT") is None
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-comment-idempotent")
def test_schema_runtime_leaves_matching_comment_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    comment = "Sales reporting schema"
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f"COMMENT ON SCHEMA \"{schema_name}\" IS '{comment}'"
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "comment": comment}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-comment-check-mode")
def test_schema_runtime_predicts_comment_change_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(exasol_login_vars, f"COMMENT ON SCHEMA \"{schema_name}\" IS 'Old'")

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "comment": "New"},
        check_mode=True,
    )

    assert result["executed_queries"] == [
        f"COMMENT ON SCHEMA \"{schema_name}\" IS 'New'"
    ]
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_COMMENT")
        == "Old"
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-comment-check-mode-idempotent")
def test_schema_runtime_check_mode_predicts_no_comment_change_when_matching(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    comment = "Sales reporting schema"
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f"COMMENT ON SCHEMA \"{schema_name}\" IS '{comment}'"
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "comment": comment},
        check_mode=True,
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert (
        _schema_metadata_value(exasol_login_vars, schema_name, "SCHEMA_COMMENT")
        == comment
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-rename")
def test_schema_runtime_renames_schema(exasol_login_vars: dict[str, object]) -> None:
    source = unique_name("ANSIBLE_SOURCE_SCHEMA")
    target = unique_name("ANSIBLE_TARGET_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{source}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": source, "new_name": target}
    )

    assert result["schema"] == target
    assert result["executed_queries"] == [f'RENAME SCHEMA "{source}" TO "{target}"']
    assert _schema_count(exasol_login_vars, source) == 0
    assert _schema_count(exasol_login_vars, target) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-rename-idempotent")
def test_schema_runtime_recognizes_existing_rename_target(
    exasol_login_vars: dict[str, object],
) -> None:
    source = unique_name("ANSIBLE_SOURCE_SCHEMA")
    target = unique_name("ANSIBLE_TARGET_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{target}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": source, "new_name": target}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert _schema_count(exasol_login_vars, source) == 0
    assert _schema_count(exasol_login_vars, target) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-rename-check-mode")
def test_schema_runtime_predicts_rename_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    source = unique_name("ANSIBLE_SOURCE_SCHEMA")
    target = unique_name("ANSIBLE_TARGET_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{source}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": source, "new_name": target}, check_mode=True
    )

    assert result["executed_queries"] == [f'RENAME SCHEMA "{source}" TO "{target}"']
    assert _schema_count(exasol_login_vars, source) == 1
    assert _schema_count(exasol_login_vars, target) == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-rename-check-mode-idempotent")
def test_schema_runtime_check_mode_predicts_no_rename_when_already_renamed(
    exasol_login_vars: dict[str, object],
) -> None:
    source = unique_name("ANSIBLE_SOURCE_SCHEMA")
    target = unique_name("ANSIBLE_TARGET_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{target}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": source, "new_name": target}, check_mode=True
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert _schema_count(exasol_login_vars, source) == 0
    assert _schema_count(exasol_login_vars, target) == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-set-raw-size-limit")
def test_schema_runtime_sets_raw_size_limit(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "raw_size_limit": 1048576}
    )

    assert result["executed_queries"] == [
        f'ALTER SCHEMA "{schema_name}" SET RAW_SIZE_LIMIT = 1048576'
    ]
    assert _raw_size_limit(exasol_login_vars, schema_name) == 1048576


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-change-raw-size-limit")
def test_schema_runtime_changes_raw_size_limit(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars,
        f'ALTER SCHEMA "{schema_name}" SET RAW_SIZE_LIMIT = 1024',
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "raw_size_limit": 2048}
    )

    assert result["changed"] is True
    assert _raw_size_limit(exasol_login_vars, schema_name) == 2048


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-raw-size-limit-idempotent")
def test_schema_runtime_leaves_matching_raw_size_limit_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f'ALTER SCHEMA "{schema_name}" SET RAW_SIZE_LIMIT = 2048'
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "raw_size_limit": 2048}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-raw-size-limit-check-mode")
def test_schema_runtime_predicts_raw_size_limit_change_without_writing(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f'ALTER SCHEMA "{schema_name}" SET RAW_SIZE_LIMIT = 1024'
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "raw_size_limit": 2048},
        check_mode=True,
    )

    assert result["changed"] is True
    assert _raw_size_limit(exasol_login_vars, schema_name) == 1024


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-raw-size-limit-check-mode-idempotent")
def test_schema_runtime_check_mode_predicts_no_raw_size_limit_change_when_matching(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(
        exasol_login_vars, f'ALTER SCHEMA "{schema_name}" SET RAW_SIZE_LIMIT = 2048'
    )

    result = exasol_schema.run_schema(
        {**exasol_login_vars, "name": schema_name, "raw_size_limit": 2048},
        check_mode=True,
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert _raw_size_limit(exasol_login_vars, schema_name) == 2048


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-schema-drop-non-empty-without-cascade")
def test_schema_runtime_does_not_drop_non_empty_schema_without_cascade(
    exasol_login_vars: dict[str, object],
) -> None:
    schema_name = unique_name("ANSIBLE_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(exasol_login_vars, f'CREATE TABLE "{schema_name}"."T" (ID DECIMAL)')

    with pytest.raises(Exception, match="(?i)cascade"):
        exasol_schema.run_schema(
            {**exasol_login_vars, "name": schema_name, "state": "absent"}
        )

    assert _schema_count(exasol_login_vars, schema_name) == 1
    assert _table_count(exasol_login_vars, schema_name, "T") == 1


def _schema_count(login_vars: dict[str, object], schema_name: str) -> int:
    return catalog_count(
        login_vars,
        table="EXA_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )


def _schema_metadata_value(
    login_vars: dict[str, object], schema_name: str, column: str
) -> object:
    schema_literal = common_query.quote_sql_string_literal(schema_name)
    with exasol_query.connect_to_exasol(
        login_vars, module_name="schema integration verification"
    ) as connection:
        rows = connection.execute(
            f"SELECT {column} FROM EXA_SCHEMAS WHERE SCHEMA_NAME = {schema_literal}"
        ).fetchall()
    row = rows[0]
    return row[column] if isinstance(row, dict) else row[0]


def _raw_size_limit(login_vars: dict[str, object], schema_name: str) -> int | None:
    value = _object_size_value(login_vars, schema_name, "RAW_OBJECT_SIZE_LIMIT")
    return None if value is None else int(value)


def _object_size_value(
    login_vars: dict[str, object], schema_name: str, column: str
) -> object:
    schema_literal = common_query.quote_sql_string_literal(schema_name)
    with exasol_query.connect_to_exasol(
        login_vars, module_name="schema integration verification"
    ) as connection:
        rows = connection.execute(
            f"SELECT {column} FROM EXA_ALL_OBJECT_SIZES "
            f"WHERE OBJECT_TYPE = 'SCHEMA' AND OBJECT_NAME = {schema_literal}"
        ).fetchall()
    row = rows[0]
    return row[column] if isinstance(row, dict) else row[0]


def _table_count(
    login_vars: dict[str, object], schema_name: str, table_name: str
) -> int:
    schema_literal = common_query.quote_sql_string_literal(schema_name)
    table_literal = common_query.quote_sql_string_literal(table_name)
    with exasol_query.connect_to_exasol(
        login_vars, module_name="schema integration verification"
    ) as connection:
        rows = connection.execute(
            "SELECT COUNT(*) AS TABLE_COUNT FROM EXA_ALL_TABLES "
            f"WHERE TABLE_SCHEMA = {schema_literal} AND TABLE_NAME = {table_literal}"
        ).fetchall()
    row = rows[0]
    return int(row["TABLE_COUNT"] if isinstance(row, dict) else row[0])
