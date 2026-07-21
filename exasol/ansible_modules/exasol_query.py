"""Runtime logic for direct Exasol SQL execution from playbooks."""

from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from typing import (
    Any,
    cast,
)

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_query import ExasolQueryResult

READ_ONLY_LEADING_KEYWORDS = common_query.READ_ONLY_LEADING_KEYWORDS
SQLGLOT_DIALECT = common_query.SQLGLOT_DIALECT

exasol_connection_argument_spec = common_query.exasol_connection_argument_spec
connection_parameters_with_defaults = common_query.connection_parameters_with_defaults
build_exasol_dsn = common_query.build_exasol_dsn
build_exasol_connect_kwargs = common_query.build_exasol_connect_kwargs
connect_to_exasol = common_query.connect_to_exasol
normalized_exasol_error_message = common_query.normalized_exasol_error_message
is_authentication_error = common_query.is_authentication_error
sanitize_error_message = common_query.sanitize_error_message
normalize_query_list = common_query.normalize_query_list
last_available_query_result = common_query.last_available_query_result
prepare_query = common_query.prepare_query
fetch_result_rows = common_query.fetch_result_rows
statement_rowcount = common_query.statement_rowcount
statement_execution_time_ms = common_query.statement_execution_time_ms
to_json_safe = common_query.to_json_safe
rows_to_json_safe = common_query.rows_to_json_safe
sqlglot_tokens = common_query.sqlglot_tokens
sqlglot_token_type = common_query.sqlglot_token_type
_sqlglot_tokens = common_query.sqlglot_tokens
_sqlglot_token_type = common_query.sqlglot_token_type
_missing_sqlglot_error = common_query.missing_sqlglot_error
is_read_only_query = common_query.is_read_only_query


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the query module."""
    return {
        **exasol_connection_argument_spec(),
        "query": {"type": "raw", "required": True},
        "positional_args": {"type": "list", "elements": "raw"},
        "named_args": {"type": "dict"},
    }


def execute_queries(
    connection: object,
    query: str | list[str],
    positional_args: Sequence[object] | None = None,
    named_args: Mapping[str, object] | None = None,
) -> ExasolQueryResult:
    """Execute statements and report changed=True for non-read-only SQL."""
    queries = normalize_query_list(query)
    result = common_query.execute_queries(
        connection,
        queries,
        positional_args=positional_args,
        named_args=named_args,
    )
    result["changed"] = any(not is_read_only_query(statement) for statement in queries)
    return result


def check_mode_result(queries: list[str]) -> ExasolQueryResult | None:
    """Return the predicted result for check mode when statements would write."""
    if all(is_read_only_query(item) for item in queries):
        return None

    return {
        "changed": True,
        "query_result": [],
        "query_all_results": [],
        "executed_queries": queries,
        "rowcount": [],
        "execution_time_ms": [],
    }


def run_query(params: Mapping[str, Any]) -> ExasolQueryResult:
    """Connect to Exasol and execute query parameters."""
    with connect_to_exasol(
        params,
        module_name="exasol_query",
    ) as connection:
        return execute_queries(
            connection,
            params["query"],
            positional_args=cast(
                Sequence[object] | None, params.get("positional_args")
            ),
            named_args=cast(Mapping[str, object] | None, params.get("named_args")),
        )
