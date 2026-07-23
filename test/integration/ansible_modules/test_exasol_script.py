"""Pure Python backend integration tests for the script runtime."""

from __future__ import annotations

import pyexasol
import pytest
from ansible_modules.common_helpers import (
    execute_sql,
    unique_name,
)
from common.catalog_assertions import catalog_count

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
@pytest.mark.scenario_id(
    "exasol-script-execute-multiple-script-bodies-terminated-by-slash"
)
# [itest -> dsn~exasol-script-execution-via-pyexasol~1]
def test_script_runtime_executes_multiple_script_bodies_terminated_by_slash(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify pyexasol splits two standalone-slash script bodies correctly."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_UDF_SCHEMA")
    first_script_name = unique_name("FIRST_VALUE")
    second_script_name = unique_name("SECOND_VALUE")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    script = (
        f'CREATE SCRIPT "{schema_name}"."{first_script_name}" AS\n'
        "x = 1; y = 2\n"
        "/\n"
        f'CREATE SCRIPT "{schema_name}"."{second_script_name}" AS\n'
        "x = 3; y = 4\n"
        "/\n"
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    first_script_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCRIPTS",
        column="SCRIPT_NAME",
        object_name=first_script_name,
        result_key="FIRST_SCRIPT_COUNT",
    )
    second_script_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_SCRIPTS",
        column="SCRIPT_NAME",
        object_name=second_script_name,
        result_key="SECOND_SCRIPT_COUNT",
    )

    assert result["changed"] is True
    assert len(result["executed_queries"]) == 2
    assert "x = 1; y = 2" in result["executed_queries"][0]
    assert "x = 3; y = 4" in result["executed_queries"][1]
    assert first_script_count == 1
    assert second_script_count == 1


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

    with pytest.raises(pyexasol.ExaQueryError) as error_info:
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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-script-check-mode-predicts-mixed-write-and-read-script"
)
# [itest -> dsn~exasol-script-execution-via-pyexasol~1]
def test_script_runtime_check_mode_predicts_mixed_write_and_read_script(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a mixed script is predicted as one unexecuted write script."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_CHECK_MODE_SCHEMA")
    script = f'CREATE SCHEMA "{schema_name}";\nSELECT 1 AS A;\n'

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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-script-semicolon-in-string-literal-does-not-split-statement"
)
def test_script_runtime_semicolon_in_string_literal_does_not_split_statement(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a semicolon inside a string literal does not terminate a statement early."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_LITERAL_SCHEMA")
    execute_sql(exasol_login_vars, f'CREATE SCHEMA "{schema_name}"')
    execute_sql(exasol_login_vars, f'CREATE TABLE "{schema_name}"."T" (V VARCHAR(20))')
    script = (
        f'INSERT INTO "{schema_name}"."T" VALUES (\'a;b\');\n'
        f'SELECT V FROM "{schema_name}"."T";\n'
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    assert result["changed"] is True
    assert len(result["executed_queries"]) == 2
    assert result["query_result"] == [{"V": "a;b"}]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-semicolon-in-comment-does-not-split-statement")
def test_script_runtime_semicolon_in_comment_does_not_split_statement(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify semicolons inside comments do not terminate statements early."""
    script = (
        "-- a comment with a ; semicolon\n"
        "SELECT 1 AS A;\n"
        "/* a block comment with a ; semicolon */\n"
        "SELECT 2 AS B;\n"
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    assert result["changed"] is False
    assert len(result["executed_queries"]) == 2


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-execute-script-invocation-side-effect")
def test_script_runtime_execute_script_invocation_side_effect(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify EXECUTE SCRIPT invoking a created script has a write side effect."""
    schema_name = unique_name("ANSIBLE_PYTHON_SCRIPT_EXEC_SCHEMA")
    script_name = unique_name("CREATE_MARKER")
    table_name = "MARKER"
    script = (
        f'CREATE SCHEMA "{schema_name}";\n'
        f'CREATE SCRIPT "{schema_name}"."{script_name}" AS\n'
        f'query([[CREATE TABLE "{schema_name}"."{table_name}" (ID DECIMAL(18,0))]])\n'
        "/\n"
        f'EXECUTE SCRIPT "{schema_name}"."{script_name}";\n'
    )

    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    table_count = catalog_count(
        exasol_login_vars,
        table="EXA_ALL_TABLES",
        column="TABLE_NAME",
        object_name=table_name,
        result_key="TABLE_COUNT",
    )

    assert result["changed"] is True
    assert len(result["executed_queries"]) == 3
    assert table_count == 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-script-empty-script-executes-nothing")
def test_script_runtime_empty_script_executes_nothing(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a script containing only blank lines and a comment executes nothing."""
    script = "\n-- nothing to do\n\n"

    predicted_result = exasol_script.check_mode_result(script)
    result = exasol_script.run_script({**exasol_login_vars, "script": script})

    assert predicted_result is None
    assert result["changed"] is False
    assert result["executed_queries"] == []
