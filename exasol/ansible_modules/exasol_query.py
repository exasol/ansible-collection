"""Shared helpers for Exasol Ansible collection modules."""

from __future__ import annotations

import base64
import copy
import datetime as dt
import math
import ssl
from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)
from decimal import Decimal
from typing import (
    Protocol,
    TypeAlias,
    TypedDict,
    cast,
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
QueryParameters: TypeAlias = dict[str, object]
AnsibleOptionSpec: TypeAlias = dict[str, object]
AnsibleArgumentSpec: TypeAlias = dict[str, AnsibleOptionSpec]


class ExasolQueryResult(TypedDict):
    """Public result shape returned by the exasol_query module."""

    changed: bool
    query_result: list[JsonValue]
    query_all_results: list[list[JsonValue]]
    executed_queries: list[str]
    rowcount: list[int]
    execution_time_ms: list[float]


class _ResultStatement(Protocol):
    result_type: str

    def fetchall(self) -> Sequence[object]:
        """Return all rows from the statement."""

    def rowcount(self) -> int:
        """Return selected or affected row count."""


class _ExasolConnection(Protocol):
    def execute(
        self,
        query: str,
        query_params: Mapping[str, object] | None = None,
    ) -> _ResultStatement:
        """Execute SQL and return a statement object."""


class _SqlglotToken(Protocol):
    token_type: object
    text: str
    start: int
    end: int


class _SqlglotTokenizer(Protocol):
    def tokenize(self, query: str) -> list[_SqlglotToken]:
        """Tokenize SQL text."""


class _SqlglotTokenizerFactory(Protocol):
    def __call__(self, *, dialect: str) -> _SqlglotTokenizer:
        """Create a tokenizer for a SQL dialect."""


class _SqlglotExpression(Protocol):
    args: Mapping[str, object]

    def find_all(
        self,
        *expression_types: type["_SqlglotExpression"],
    ) -> Iterable["_SqlglotExpression"]:
        """Find matching expressions in the parsed SQL tree."""


class _SqlglotModule(Protocol):
    Tokenizer: _SqlglotTokenizerFactory

    def parse(
        self,
        sql: str,
        *,
        read: str,
    ) -> list[_SqlglotExpression | None]:
        """Parse SQL text into expressions."""


class _SqlglotTokenType(Protocol):
    PLACEHOLDER: object
    COLON: object


class _SqlglotExpressionTypes(Protocol):
    Command: type[_SqlglotExpression]
    Describe: type[_SqlglotExpression]
    Query: type[_SqlglotExpression]
    Select: type[_SqlglotExpression]
    Values: type[_SqlglotExpression]


DEFAULT_LOGIN_HOST = "localhost"
DEFAULT_LOGIN_PORT = 8563
DEFAULT_LOGIN_DB = ""
DEFAULT_AUTOCOMMIT = True
DEFAULT_FETCH_SIZE = 5000
DEFAULT_COMPRESSION = False
DEFAULT_VALIDATE_CERTS = True
REDACTED = "********"

CONNECTION_DEFAULTS: dict[str, object] = {
    "login_host": DEFAULT_LOGIN_HOST,
    "login_port": DEFAULT_LOGIN_PORT,
    "login_db": DEFAULT_LOGIN_DB,
    "autocommit": DEFAULT_AUTOCOMMIT,
    "fetch_size": DEFAULT_FETCH_SIZE,
    "compression": DEFAULT_COMPRESSION,
    "validate_certs": DEFAULT_VALIDATE_CERTS,
    "client_kwargs": {},
}
OPTIONAL_CONNECTION_PARAMETERS = (
    "login_user",
    "login_password",
    "ca_cert",
    "certificate_fingerprint",
)
SENSITIVE_CLIENT_KWARGS = {
    "access_token",
    "auth_token",
    "client_secret",
    "password",
    "passphrase",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}
SENSITIVE_CLIENT_KWARG_MARKERS = (
    "password",
    "passphrase",
    "private_key",
    "secret",
    "token",
)
SQLGLOT_DIALECT = "exasol"
READ_ONLY_LEADING_KEYWORDS = frozenset(
    {
        "DESCRIBE",
        "EXPLAIN",
        "SHOW",
        "VALUES",
    }
)

_AUTHENTICATION_MARKERS = (
    "auth",
    "credential",
    "login",
    "password",
)


def exasol_connection_argument_spec() -> AnsibleArgumentSpec:
    """Return the common Ansible connection argument spec for Exasol modules."""
    return {
        "login_host": {"type": "str", "default": DEFAULT_LOGIN_HOST},
        "login_port": {"type": "int", "default": DEFAULT_LOGIN_PORT},
        "login_user": {"type": "str", "required": True},
        "login_password": {"type": "str", "no_log": True},
        "login_db": {
            "type": "str",
            "default": DEFAULT_LOGIN_DB,
            "aliases": ["login_schema"],
        },
        "autocommit": {"type": "bool", "default": DEFAULT_AUTOCOMMIT},
        "fetch_size": {"type": "int", "default": DEFAULT_FETCH_SIZE},
        "compression": {"type": "bool", "default": DEFAULT_COMPRESSION},
        "validate_certs": {"type": "bool", "default": DEFAULT_VALIDATE_CERTS},
        "ca_cert": {"type": "path"},
        "certificate_fingerprint": {"type": "str"},
        "client_kwargs": {"type": "dict", "default": {}, "no_log": True},
    }


def connection_parameters_with_defaults(
    params: Mapping[str, object],
) -> dict[str, object]:
    """Return connection parameters with shared defaults applied."""
    resolved = copy.deepcopy(CONNECTION_DEFAULTS)

    for name in CONNECTION_DEFAULTS:
        if name in params:
            resolved[name] = params[name]

    # Keep the familiar Ansible database-module option name even though Exasol
    # opens schemas rather than per-connection databases.
    if "login_schema" in params and "login_db" not in params:
        resolved["login_db"] = params["login_schema"]

    for name in OPTIONAL_CONNECTION_PARAMETERS:
        if name in params:
            resolved[name] = params[name]

    return resolved


def build_exasol_dsn(params: Mapping[str, object]) -> str:
    """Build a pyexasol DSN from Ansible connection parameters."""
    resolved = connection_parameters_with_defaults(params)
    host = resolved["login_host"]
    port = resolved["login_port"]
    fingerprint = resolved.get("certificate_fingerprint")

    if fingerprint:
        return f"{host}/{fingerprint}:{port}"

    return f"{host}:{port}"


def build_exasol_connect_kwargs(params: Mapping[str, object]) -> dict[str, object]:
    """Map connection parameters to pyexasol.connect keyword arguments."""
    resolved = connection_parameters_with_defaults(params)
    client_kwargs = dict(_mapping_or_empty(resolved.get("client_kwargs")))

    connect_kwargs = {
        "dsn": build_exasol_dsn(resolved),
        "user": resolved.get("login_user"),
        "password": resolved.get("login_password"),
        "schema": resolved.get("login_db") or "",
        "autocommit": resolved["autocommit"],
        "fetch_size_bytes": resolved["fetch_size"],
        "compression": resolved["compression"],
        "encryption": True,
        "fetch_dict": True,
    }

    ca_cert = resolved.get("ca_cert")

    if (
        not resolved["validate_certs"]
        or resolved.get("certificate_fingerprint")
        or ca_cert
    ):
        websocket_sslopt = dict(
            _mapping_or_empty(client_kwargs.get("websocket_sslopt"))
        )
        if ca_cert and resolved["validate_certs"]:
            websocket_sslopt["ca_certs"] = ca_cert
        websocket_sslopt["cert_reqs"] = (
            ssl.CERT_REQUIRED if resolved["validate_certs"] else ssl.CERT_NONE
        )
        connect_kwargs["websocket_sslopt"] = websocket_sslopt

    client_kwargs.update(connect_kwargs)
    return client_kwargs


def _mapping_or_empty(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)

    return {}


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol operation",
) -> str:
    """Return a sanitized user-facing Exasol failure message."""
    safe_message = sanitize_error_message(error, params)

    if is_authentication_error(safe_message):
        return "Failed to authenticate with Exasol. Verify the supplied credentials."

    return f"{operation} failed: {safe_message}"


def is_authentication_error(message: str) -> bool:
    """Return whether an error message appears to describe authentication failure."""
    normalized = message.lower()

    return any(marker in normalized for marker in _AUTHENTICATION_MARKERS)


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact known secret values from an error string."""
    message = str(error)

    for secret in sorted(_secret_values(params), key=len, reverse=True):
        message = message.replace(secret, REDACTED)

    return message


def normalize_query_list(query: object) -> list[str]:
    """Normalize an Ansible query argument into an ordered statement list."""
    if isinstance(query, str):
        return [query]

    if isinstance(query, list) and all(isinstance(item, str) for item in query):
        return list(query)

    raise ValueError("query must be a string or a list of strings.")


def execute_queries(
    connection: _ExasolConnection,
    query: str | list[str],
    positional_args: Sequence[object] | None = None,
    named_args: Mapping[str, object] | None = None,
) -> ExasolQueryResult:
    """Execute one or more Exasol statements and return Ansible result values."""
    queries = normalize_query_list(query)
    all_results: list[list[JsonValue]] = []
    rowcounts: list[int] = []
    execution_time_ms: list[float] = []

    for statement in queries:
        prepared_statement, query_params = prepare_query(
            statement,
            positional_args=positional_args,
            named_args=named_args,
        )
        cursor = connection.execute(prepared_statement, query_params or None)
        all_results.append(fetch_result_rows(cursor))
        rowcounts.append(statement_rowcount(cursor))
        execution_time_ms.append(statement_execution_time_ms(cursor))

    return {
        "changed": any(not is_read_only_query(statement) for statement in queries),
        "query_result": last_available_query_result(all_results),
        "query_all_results": all_results,
        "executed_queries": queries,
        "rowcount": rowcounts,
        "execution_time_ms": execution_time_ms,
    }


def last_available_query_result(
    all_results: Sequence[list[JsonValue]],
) -> list[JsonValue]:
    """Return rows from the last executed statement, if any."""
    return all_results[-1] if all_results else []


def prepare_query(
    query: str,
    positional_args: Sequence[object] | None = None,
    named_args: Mapping[str, object] | None = None,
) -> tuple[str, QueryParameters]:
    """Translate Ansible-style placeholders into pyexasol formatter placeholders."""
    positional_values = list(positional_args or [])
    named_values = dict(named_args or {})
    query_params: QueryParameters = {}
    named_placeholders: set[str] = set()
    positional_index = 0
    rewritten = []
    rewrite_index = 0
    tokens = _sqlglot_tokens(query)
    token_type = _sqlglot_token_type()
    token_index = 0

    while token_index < len(tokens):
        token = tokens[token_index]
        replacement = None
        replacement_end = token.end + 1
        next_token_index = token_index + 1

        if token.token_type == token_type.PLACEHOLDER and token.text == "?":
            replacement, positional_index = _prepare_positional_placeholder(
                positional_values,
                positional_index,
                query_params,
            )
        else:
            named_placeholder = _prepare_named_placeholder(
                query,
                tokens,
                token_index,
                named_values,
                query_params,
                named_placeholders,
                token_type,
            )
            if named_placeholder is not None:
                replacement, replacement_end, next_token_index = named_placeholder

        if replacement is not None:
            rewritten.append(query[rewrite_index : token.start])
            rewritten.append(replacement)
            rewrite_index = replacement_end

        token_index = next_token_index

    rewritten.append(query[rewrite_index:])

    if positional_index < len(positional_values):
        raise ValueError(
            _positional_args_mismatch_message(
                placeholders=positional_index,
                values=len(positional_values),
            )
        )

    _raise_for_unused_named_args(named_values, named_placeholders)

    return "".join(rewritten), query_params


def _sqlglot_tokens(query: str) -> list[_SqlglotToken]:
    try:
        import sqlglot
    except ImportError as error:
        raise _missing_sqlglot_error() from error

    return (
        cast(_SqlglotModule, sqlglot).Tokenizer(dialect=SQLGLOT_DIALECT).tokenize(query)
    )


def _sqlglot_token_type() -> _SqlglotTokenType:
    try:
        from sqlglot.tokens import TokenType
    except ImportError as error:
        raise _missing_sqlglot_error() from error

    return cast(_SqlglotTokenType, TokenType)


def _sqlglot_parser_runtime() -> tuple[
    _SqlglotModule,
    _SqlglotExpressionTypes,
    tuple[type[Exception], ...],
]:
    try:
        import sqlglot
        from sqlglot import exp
        from sqlglot.errors import (
            ParseError,
            TokenError,
        )
    except ImportError as error:
        raise _missing_sqlglot_error() from error

    return (
        cast(_SqlglotModule, sqlglot),
        cast(_SqlglotExpressionTypes, exp),
        (ParseError, TokenError),
    )


def _missing_sqlglot_error() -> RuntimeError:
    return RuntimeError(
        "sqlglot is required to parse Exasol queries. "
        "Install exasol-ansible-modules with its runtime dependencies."
    )


def _prepare_positional_placeholder(
    positional_values: Sequence[object],
    positional_index: int,
    query_params: QueryParameters,
) -> tuple[str, int]:
    if positional_index >= len(positional_values):
        raise ValueError(
            _positional_args_mismatch_message(
                placeholders=positional_index + 1,
                values=len(positional_values),
            )
        )

    name = f"__pos_{positional_index}"
    value = positional_values[positional_index]
    query_params[name] = _query_param_value(value)
    return _pyexasol_placeholder(name, value), positional_index + 1


def _positional_args_mismatch_message(placeholders: int, values: int) -> str:
    return (
        "positional_args does not match the SQL positional placeholders: "
        f"the query contains {placeholders} '?' placeholder(s), but "
        f"positional_args contains {values} value(s). Add a value for each '?' "
        "placeholder or remove the extra positional_args entries."
    )


def _prepare_named_placeholder(
    query: str,
    tokens: Sequence[_SqlglotToken],
    token_index: int,
    named_values: Mapping[str, object],
    query_params: QueryParameters,
    named_placeholders: set[str],
    token_type: _SqlglotTokenType,
) -> tuple[str, int, int] | None:
    token = tokens[token_index]
    next_token_index = token_index + 1
    if token.token_type != token_type.COLON or next_token_index >= len(tokens):
        return None

    next_token = tokens[next_token_index]
    if next_token.start != token.end + 1:
        return None

    name = query[next_token.start : next_token.end + 1]
    if name != next_token.text or not name.isidentifier():
        return None

    if name not in named_values:
        raise ValueError(_missing_named_arg_message(name))

    value = named_values[name]
    query_params[name] = _query_param_value(value)
    named_placeholders.add(name)
    return _pyexasol_placeholder(name, value), next_token.end + 1, token_index + 2


def _missing_named_arg_message(name: str) -> str:
    return (
        "named_args does not match the SQL named placeholders: the query contains "
        f"named placeholder ':{name}', but named_args does not contain a value "
        "for it. Add a value for each ':name' placeholder."
    )


def _raise_for_unused_named_args(
    named_values: Mapping[str, object],
    named_placeholders: set[str],
) -> None:
    unused_names = sorted(set(named_values) - named_placeholders)
    if not unused_names:
        return

    raise ValueError(
        "named_args contains unused value(s): "
        f"{', '.join(unused_names)}; remove the extra named_args entries or add "
        "matching ':name' placeholders."
    )


def fetch_result_rows(statement: _ResultStatement) -> list[JsonValue]:
    """Fetch statement rows as JSON-safe dictionaries when rows are available."""
    if getattr(statement, "result_type", None) != "resultSet":
        return []

    rows = list(statement.fetchall())

    if rows and not isinstance(rows[0], Mapping):
        column_names = _statement_column_names(statement)
        rows = [
            dict(zip(column_names, row))
            for row in cast(Iterable[Iterable[object]], rows)
        ]

    return rows_to_json_safe(rows)


def statement_rowcount(statement: object) -> int:
    """Return a pyexasol statement rowcount as an integer."""
    return int(cast(_ResultStatement, statement).rowcount())


def statement_execution_time_ms(statement: object) -> float:
    """Return pyexasol statement execution time in milliseconds."""
    return float(getattr(statement, "execution_time", 0) or 0) * 1000


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

    return first_token.text.upper() in READ_ONLY_LEADING_KEYWORDS


def _statement_leading_keywords(query: str) -> list[str]:
    keywords = []
    start_of_statement = True

    for token in _sqlglot_tokens(query):
        if token.text == ";":
            start_of_statement = True
            continue

        if start_of_statement:
            keywords.append(token.text.upper())
            start_of_statement = False

    return keywords


def _first_sqlglot_token(query: str) -> _SqlglotToken | None:
    tokens = _sqlglot_tokens(query)
    return tokens[0] if tokens else None


def to_json_safe(value: object) -> JsonValue:
    """Convert pyexasol result values into JSON-safe Ansible return values."""
    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()

    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")

    if isinstance(value, Mapping):
        return {
            str(to_json_safe(key)): to_json_safe(item) for key, item in value.items()
        }

    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]

    if isinstance(value, list):
        return [to_json_safe(item) for item in value]

    return str(value)


def rows_to_json_safe(rows: Iterable[object]) -> list[JsonValue]:
    """Convert Exasol result rows into JSON-safe values."""
    return [to_json_safe(row) for row in rows]


def _statement_column_names(statement: object) -> list[str]:
    column_names = getattr(statement, "column_names", None)
    if callable(column_names):
        return list(column_names())

    return list(getattr(statement, "col_names", []))


def _secret_values(params: Mapping[str, object]) -> set[str]:
    secrets = set()

    password = params.get("login_password")
    if isinstance(password, str) and password:
        secrets.add(password)

    _collect_sensitive_values(params.get("client_kwargs"), secrets)

    _collect_sensitive_values(params.get("named_args"), secrets)

    return secrets


def _collect_sensitive_values(value: object, secrets: set[str], key: str = "") -> None:
    if isinstance(value, Mapping):
        for item_key, item_value in value.items():
            _collect_sensitive_values(
                item_value,
                secrets,
                key=str(item_key).lower(),
            )
        return

    if isinstance(value, (list, tuple)):
        for item in value:
            _collect_sensitive_values(item, secrets, key=key)
        return

    if _is_sensitive_client_kwarg(key) and isinstance(value, str) and value:
        secrets.add(value)


def _is_sensitive_client_kwarg(key: str) -> bool:
    return key in SENSITIVE_CLIENT_KWARGS or any(
        marker in key for marker in SENSITIVE_CLIENT_KWARG_MARKERS
    )


def _pyexasol_placeholder(name: str, value: object) -> str:
    conversion = _pyexasol_conversion(value)
    if conversion:
        return f"{{{name}!{conversion}}}"

    return f"{{{name}}}"


def _pyexasol_conversion(value: object) -> str:
    if isinstance(value, bool):
        return "r"

    if isinstance(value, int):
        return "d"

    if isinstance(value, Decimal):
        return "d"

    if isinstance(value, float):
        return "f"

    return ""


def _query_param_value(value: object) -> object:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    return value
