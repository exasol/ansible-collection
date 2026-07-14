"""Runtime logic for direct Exasol SQL execution from playbooks."""

from __future__ import annotations

from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)
from typing import (
    Any,
    Protocol,
    cast,
)

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_query import ExasolQueryResult

READ_ONLY_LEADING_KEYWORDS = frozenset(
    {
        "DESCRIBE",
        "EXPLAIN",
        "SHOW",
        "VALUES",
    }
)
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


class _SqlglotExpression(Protocol):
    args: Mapping[str, object]

    def find_all(
        self,
        *expression_types: type[_SqlglotExpression],
    ) -> Iterable[_SqlglotExpression]:
        """Find matching expressions in the parsed SQL tree."""


class _SqlglotModule(Protocol):
    def parse(
        self,
        sql: str,
        *,
        read: str,
    ) -> list[_SqlglotExpression | None]:
        """Parse SQL text into expressions."""


class _SqlglotExpressionTypes(Protocol):
    Command: type[_SqlglotExpression]
    Describe: type[_SqlglotExpression]
    Query: type[_SqlglotExpression]
    Select: type[_SqlglotExpression]
    Values: type[_SqlglotExpression]


class _SqlglotToken(Protocol):
    text: str


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


def is_read_only_query(query: str) -> bool:
    """Return whether a SQL statement is conservatively read-only using SQLGlot AST."""
    sqlglot, exp, parse_errors = _sqlglot_parser_runtime()

    try:
        parsed = sqlglot.parse(query, read=SQLGLOT_DIALECT)
        leading_keywords = _statement_leading_keywords(query)

        if not parsed or len(parsed) != len(leading_keywords):
            return False

        return all(
            expr is not None and _is_read_only_expression(expr, exp, leading_keyword)
            for expr, leading_keyword in zip(parsed, leading_keywords)
        )

    except parse_errors:
        return _is_read_only_by_token(query)


def _sqlglot_parser_runtime() -> tuple[
    _SqlglotModule,
    _SqlglotExpressionTypes,
    tuple[type[Exception], ...],
]:
    sqlglot = common_query.import_sqlglot_module("sqlglot")
    exp = getattr(sqlglot, "exp")
    errors = common_query.import_sqlglot_module("sqlglot.errors")

    return (
        cast(_SqlglotModule, sqlglot),
        cast(_SqlglotExpressionTypes, exp),
        (
            cast(type[Exception], getattr(errors, "ParseError")),
            cast(type[Exception], getattr(errors, "TokenError")),
        ),
    )


def _is_read_only_expression(
    expression: _SqlglotExpression,
    exp: _SqlglotExpressionTypes,
    leading_keyword: str,
) -> bool:
    if _contains_select_into(expression, exp):
        return False

    if isinstance(expression, exp.Command):
        return leading_keyword in READ_ONLY_LEADING_KEYWORDS

    if isinstance(expression, exp.Describe):
        return leading_keyword == "DESCRIBE"

    if isinstance(expression, exp.Values):
        return leading_keyword == "VALUES"

    return isinstance(expression, exp.Query)


def _contains_select_into(
    expression: _SqlglotExpression,
    exp: _SqlglotExpressionTypes,
) -> bool:
    return any(
        select.args.get("into") is not None
        for select in expression.find_all(exp.Select)
    )


def _is_read_only_by_token(query: str) -> bool:
    first_token = _first_sqlglot_token(query)

    if not first_token:
        return False

    return str(first_token.text).upper() in READ_ONLY_LEADING_KEYWORDS


def _statement_leading_keywords(query: str) -> list[str]:
    keywords = []
    start_of_statement = True

    for token in cast(list[_SqlglotToken], _sqlglot_tokens(query)):
        if token.text == ";":
            start_of_statement = True
            continue

        if start_of_statement:
            keywords.append(str(token.text).upper())
            start_of_statement = False

    return keywords


def _first_sqlglot_token(query: str) -> _SqlglotToken | None:
    tokens = cast(list[_SqlglotToken], _sqlglot_tokens(query))
    return tokens[0] if tokens else None
