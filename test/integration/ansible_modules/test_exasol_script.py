"""Pure Python backend integration tests for the script runtime."""

from __future__ import annotations

import pytest
from ansible_modules.common_helpers import (
    catalog_count,
    execute_sql,
    unique_name,
)

from exasol.ansible_modules import exasol_script


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-multi-statement-script-against-backend")
def test_script_runtime_executes_multi_statement_script_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the script runtime can execute a multi-statement script through its run helper."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_SCHEMA")
    script = (
        f'CREATE SCHEMA "{schema_name}";\n'
        f'CREATE TABLE "{schema_name}"."T" (ID DECIMAL(18,0));\n'
        f'INSERT INTO "{schema_name}"."T" VALUES (1);\n'
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        f'CREATE SCHEMA "{schema_name}"',
        f'CREATE TABLE "{schema_name}"."T" (ID DECIMAL(18,0))',
        f'INSERT INTO "{schema_name}"."T" VALUES (1)',
    ]
    assert schema_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-script-body-terminated-by-slash")
def test_script_runtime_executes_script_body_terminated_by_slash(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a script body with embedded semicolons executes as one statement."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_UDF_SCHEMA")
    script_name = unique_name("DOUBLE_VALUE")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    script = (
        f'CREATE SCRIPT "{schema_name}"."{script_name}" AS\n' "x = 1; y = 2\n" "/\n"
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    script_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCRIPTS",
        column="SCRIPT_NAME",
        object_name=script_name,
        result_key="SCRIPT_COUNT",
    )

    assert result["changed"] is True
    assert len(result["executed_queries"]) == 1
    assert "x = 1; y = 2" in result["executed_queries"][0]
    assert script_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-read-only-script-against-backend")
def test_script_runtime_executes_read_only_script_against_backend(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a script made up only of read-only statements is unchanged."""
    script = "SELECT 1 AS A;\nSELECT 2 AS B;\n"

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    assert result["changed"] is False
    assert result["executed_queries"] == ["SELECT 1 AS A", "SELECT 2 AS B"]
    assert result["query_result"] == [{"B": 2}]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-failing-statement-stops-later-statements")
def test_script_runtime_stops_after_failing_statement(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a failing statement stops later statements without undoing earlier ones."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_FAIL_SCHEMA")
    table_name = "NEVER_CREATED"
    script = (
        f'CREATE SCHEMA "{schema_name}";\n'
        "SELECT 1 FROM NO_SUCH_TABLE_AT_ALL;\n"
        f'CREATE TABLE "{schema_name}"."{table_name}" (ID DECIMAL(18,0));\n'
    )

    with pytest.raises(Exception) as error_info:
        exasol_script.run_script({**exasol_login_vars, "script": script})

    assert "NO_SUCH_TABLE_AT_ALL" in str(error_info.value)

    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )
    table_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_TABLES",
        column="TABLE_NAME",
        object_name=table_name,
        result_key="TABLE_COUNT",
    )

    assert schema_count == 1
    assert table_count == 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-check-mode-ignores-read-only-script")
def test_script_runtime_check_mode_ignores_read_only_script(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify script check mode keeps read-only scripts on the execution path."""
    script = (
        "SELECT PARAM_VALUE FROM EXA_METADATA "
        "WHERE PARAM_NAME = 'databaseProductVersion';"
    )

    predicted_result = exasol_script.check_mode_result(script)
    executed_result = exasol_script.run_script({**exasol_login_vars, "script": script})

    assert predicted_result is None
    assert executed_result["changed"] is False
    assert executed_result["query_result"]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-check-mode-predicts-write-without-execution")
def test_script_runtime_check_mode_predicts_write_without_execution(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify script check mode predicts a write script without executing it."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_CHECK_MODE_SCHEMA")
    script = f'CREATE SCHEMA "{schema_name}";\n'

    predicted_result = exasol_script.check_mode_result(script)
    schema_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCHEMAS",
        column="SCHEMA_NAME",
        object_name=schema_name,
        result_key="SCHEMA_COUNT",
    )

    assert predicted_result is not None
    assert predicted_result["changed"] is True
    assert predicted_result["executed_queries"] == [script]
    assert predicted_result["query_result"] == []
    assert schema_count == 0
