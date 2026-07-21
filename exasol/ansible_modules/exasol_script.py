"""Runtime logic for executing multi-statement Exasol SQL scripts."""

from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from typing import (
    Any,
    Protocol,
)

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_query import ExasolQueryResult
from exasol.ansible_modules.exasol_query import is_read_only_query

type ExasolScriptResult = ExasolQueryResult
type _ExasolStatement = Any


class _ScriptCapableConnection(Protocol):
    def execute_sql_script(self, script: str) -> Sequence[_ExasolStatement]:
        """Execute a multi-statement SQL script and return its statements."""


exasol_connection_argument_spec = common_query.exasol_connection_argument_spec
connection_parameters_with_defaults = common_query.connection_parameters_with_defaults
build_exasol_dsn = common_query.build_exasol_dsn
build_exasol_connect_kwargs = common_query.build_exasol_connect_kwargs
connect_to_exasol = common_query.connect_to_exasol
normalized_exasol_error_message = common_query.normalized_exasol_error_message
is_authentication_error = common_query.is_authentication_error
sanitize_error_message = common_query.sanitize_error_message
last_available_query_result = common_query.last_available_query_result
fetch_result_rows = common_query.fetch_result_rows
statement_rowcount = common_query.statement_rowcount
statement_execution_time_ms = common_query.statement_execution_time_ms
to_json_safe = common_query.to_json_safe
rows_to_json_safe = common_query.rows_to_json_safe


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the script module."""
    return {
        **exasol_connection_argument_spec(),
        "script": {"type": "str", "required": True},
    }


def execute_script(
    connection: _ScriptCapableConnection, script: str
) -> ExasolScriptResult:
    """Execute a multi-statement SQL script and report changed for any write."""
    statements = connection.execute_sql_script(script)

    executed_queries = [str(statement.query) for statement in statements]
    all_results = [fetch_result_rows(statement) for statement in statements]
    rowcounts = [statement_rowcount(statement) for statement in statements]
    execution_time_ms = [
        statement_execution_time_ms(statement) for statement in statements
    ]

    return {
        "changed": any(
            not is_read_only_query(statement_text)
            for statement_text in executed_queries
        ),
        "query_result": last_available_query_result(all_results),
        "query_all_results": all_results,
        "executed_queries": executed_queries,
        "rowcount": rowcounts,
        "execution_time_ms": execution_time_ms,
    }


def check_mode_result(script: str) -> ExasolScriptResult | None:
    """Return the predicted result for check mode when the script would write.

    Pyexasol only splits a script into individual statements as part of
    executing it, so there is no public way to predict the exact per-statement
    breakdown without running the script. Check mode therefore classifies the
    whole script as one unit: a script that is entirely read-only predicts no
    change, and any other script reports the whole script text as a single
    predicted statement instead of the real per-statement breakdown that
    execution produces.
    """
    if is_read_only_query(script):
        return None

    return {
        "changed": True,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": [script],
        "rowcount": [],
        "execution_time_ms": [],
    }


def run_script(params: Mapping[str, Any]) -> ExasolScriptResult:
    """Connect to Exasol and execute the script parameter."""
    with connect_to_exasol(
        params,
        module_name="exasol_script",
    ) as connection:
        return execute_script(connection, params["script"])
