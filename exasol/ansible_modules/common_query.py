"""Shared Exasol connection, execution, result, and error helpers."""

from __future__ import annotations

import base64
import copy
import datetime as dt
import math
import ssl
from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from contextlib import contextmanager
from decimal import Decimal
from typing import (
    Any,
    TypedDict,
    cast,
)

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
type QueryParameters = dict[str, object]
type AnsibleOptionSpec = dict[str, object]
type AnsibleArgumentSpec = dict[str, AnsibleOptionSpec]
type _ResultStatement = Any
type _ExasolConnection = Any
type _SqlglotToken = Any
type _SqlglotModule = Any
type _SqlglotTokenType = Any


class ExasolQueryResult(TypedDict):
    """Public result shape returned by the exasol_query module."""

    changed: bool
    query_result: list[JsonValue]
    query_all_results: list[list[JsonValue]]
    executed_queries: list[str]
    rowcount: list[int]
    execution_time_ms: list[float]


class _QueryRewriteParts(TypedDict):
    """Mutable state used while translating query placeholders."""

    query_params: QueryParameters
    named_placeholders: set[str]
    positional_index: int
    rewritten: list[str]
    rewrite_index: int


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
_AUTHENTICATION_MARKERS = (
    "auth",
    "credential",
    "login",
    "password",
)
_JSON_SAFE_MISSING = object()


# [impl -> dsn~mark-secret-bearing-parameters-no-log~1]
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
    fingerprint = _explicit_certificate_fingerprint(
        resolved.get("certificate_fingerprint")
    )

    if fingerprint:
        return f"{host}/{fingerprint}:{port}"

    return f"{host}:{port}"


# [impl -> dsn~encrypt-exasol-connections-by-default~2]
# [impl -> dsn~encrypted-transport-by-default~2]
# [impl -> dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1]
def build_exasol_connect_kwargs(params: Mapping[str, object]) -> dict[str, object]:
    """Map connection parameters to pyexasol.connect keyword arguments."""
    resolved = connection_parameters_with_defaults(params)
    _validate_transport_security_options(resolved)
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
    websocket_sslopt = dict(_mapping_or_empty(client_kwargs.get("websocket_sslopt")))

    if (
        websocket_sslopt
        or not resolved["validate_certs"]
        or _explicit_certificate_fingerprint(resolved.get("certificate_fingerprint"))
        or ca_cert
    ):
        if ca_cert and resolved["validate_certs"]:
            websocket_sslopt["ca_certs"] = ca_cert
        websocket_sslopt["cert_reqs"] = (
            ssl.CERT_REQUIRED if resolved["validate_certs"] else ssl.CERT_NONE
        )
        connect_kwargs["websocket_sslopt"] = websocket_sslopt

    client_kwargs.update(connect_kwargs)
    return client_kwargs


def _validate_transport_security_options(resolved: Mapping[str, object]) -> None:
    validate_certs = bool(resolved["validate_certs"])
    fingerprint = _explicit_certificate_fingerprint(
        resolved.get("certificate_fingerprint")
    )

    if not validate_certs and not fingerprint:
        raise ValueError(
            "validate_certs=false requires certificate_fingerprint so the "
            "connection keeps an explicit TLS trust anchor."
        )


def _explicit_certificate_fingerprint(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    fingerprint = value.strip()

    if not fingerprint:
        return None

    if fingerprint.casefold() == "nocertcheck":
        raise ValueError(
            "certificate_fingerprint must pin a real server certificate; "
            "'nocertcheck' disables TLS verification and is not supported."
        )

    return fingerprint


# [impl -> dsn~keep-secret-handling-transient-within-task-execution~1]
@contextmanager
def connect_to_exasol(
    params: Mapping[str, object],
    module_name: str,
) -> Iterator[_ExasolConnection]:
    """Open a pyexasol connection and always close it afterwards."""
    try:
        import pyexasol
    except ImportError as error:
        raise RuntimeError(
            f"pyexasol is required to use {module_name}. "
            "Install it in the Python environment that runs Ansible modules, "
            "for example with `python -m pip install exasol-ansible-modules`."
        ) from error

    connection = pyexasol.connect(**build_exasol_connect_kwargs(params))

    try:
        yield connection
    finally:
        connection.close()


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


# [impl -> dsn~secret-redaction~1]
# [impl -> dsn~redact-secrets-from-sql-and-surfaced-failures~1]
# [impl -> dsn~centralize-connection-parameter-mapping-and-secret-sanitization~1]
def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact known secret values from an error string."""
    message = str(error)

    for secret in sorted(_secret_values(params), key=len, reverse=True):
        message = message.replace(secret, REDACTED)

    return message


def quote_sql_string_literal(value: str) -> str:
    """Quote a string value for use as an Exasol SQL literal."""
    if not isinstance(value, str):
        raise ValueError("Exasol SQL string literal value must be a string.")

    if "\x00" in value:
        raise ValueError(
            "Exasol SQL string literal value must not contain NUL characters."
        )

    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def normalize_query_list(query: object) -> list[str]:
    """Normalize an Ansible query argument into an ordered statement list."""
    if isinstance(query, str):
        return [query]

    if isinstance(query, list) and all(isinstance(item, str) for item in query):
        return list(query)

    raise ValueError("query must be a string or a list of strings.")


# [impl -> dsn~avoid-autonomous-retry-of-privileged-actions~1]
def execute_queries(
    connection: _ExasolConnection,
    query: str | list[str],
    positional_args: Sequence[object] | None = None,
    named_args: Mapping[str, object] | None = None,
) -> ExasolQueryResult:
    """Execute one or more Exasol statements and return Ansible result values."""
    queries = normalize_query_list(query)

    # Prevent unsafe reuse of args across batch execution
    if len(queries) > 1 and (positional_args or named_args):
        raise ValueError(
            "positional_args and named_args can only be used with a single SQL "
            "statement. For statement batches, split the batch into separate "
            "exasol_query tasks or inline values in each statement."
        )

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
        "changed": False,
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
    parts = _new_query_rewrite_parts()
    tokens = sqlglot_tokens(query)
    token_type = sqlglot_token_type()
    token_index = 0

    while token_index < len(tokens):
        token = tokens[token_index]
        replacement = None
        replacement_end = token.end + 1
        next_token_index = token_index + 1

        if token.token_type == token_type.PLACEHOLDER and token.text == "?":
            replacement, parts["positional_index"] = _prepare_positional_placeholder(
                positional_values,
                parts["positional_index"],
                parts["query_params"],
            )
        else:
            named_placeholder = _match_named_placeholder(
                query,
                tokens,
                token_index,
                token_type,
            )
            if named_placeholder is not None:
                name, replacement_end, next_token_index = named_placeholder
                replacement = _bind_named_placeholder(
                    name,
                    named_values,
                    parts["query_params"],
                    parts["named_placeholders"],
                )

        if replacement is not None:
            parts["rewritten"].append(query[parts["rewrite_index"] : token.start])
            parts["rewritten"].append(replacement)
            parts["rewrite_index"] = replacement_end

        token_index = next_token_index

    parts["rewritten"].append(query[parts["rewrite_index"] :])

    if parts["positional_index"] < len(positional_values):
        raise ValueError(
            _positional_args_mismatch_message(
                placeholders=parts["positional_index"],
                values=len(positional_values),
            )
        )

    _raise_for_unused_named_args(named_values, parts["named_placeholders"])

    return "".join(parts["rewritten"]), parts["query_params"]


def _new_query_rewrite_parts() -> _QueryRewriteParts:
    return {
        "query_params": {},
        "named_placeholders": set(),
        "positional_index": 0,
        "rewritten": [],
        "rewrite_index": 0,
    }


def sqlglot_tokens(query: str) -> list[_SqlglotToken]:
    """Tokenize SQL text using the shared Exasol SQLGlot dialect."""
    sqlglot = import_sqlglot_module("sqlglot")
    return (
        cast(_SqlglotModule, sqlglot).Tokenizer(dialect=SQLGLOT_DIALECT).tokenize(query)
    )


def sqlglot_token_type() -> _SqlglotTokenType:
    """Return SQLGlot token type constants."""
    tokens = import_sqlglot_module("sqlglot.tokens")
    return cast(_SqlglotTokenType, getattr(tokens, "TokenType"))


def import_sqlglot_module(name: str) -> object:
    """Import a SQLGlot module and normalize missing-dependency failures."""
    try:
        return __import__(name, fromlist=[""])
    except ImportError as error:
        raise missing_sqlglot_error() from error


def missing_sqlglot_error() -> RuntimeError:
    """Return the shared missing-SQLGlot runtime error."""
    return RuntimeError(
        "sqlglot is required to parse Exasol queries. "
        "Install exasol-ansible-modules with its runtime dependencies."
    )


def _sqlglot_tokens(query: str) -> list[_SqlglotToken]:
    return sqlglot_tokens(query)


def _sqlglot_token_type() -> _SqlglotTokenType:
    return sqlglot_token_type()


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


def _match_named_placeholder(
    query: str,
    tokens: Sequence[_SqlglotToken],
    token_index: int,
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

    return name, next_token.end + 1, token_index + 2


def _bind_named_placeholder(
    name: str,
    named_values: Mapping[str, object],
    query_params: QueryParameters,
    named_placeholders: set[str],
) -> str:
    if name not in named_values:
        raise ValueError(_missing_named_arg_message(name))

    value = named_values[name]
    query_params[name] = _query_param_value(value)
    named_placeholders.add(name)
    return _pyexasol_placeholder(name, value)


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


def to_json_safe(value: object) -> JsonValue:
    """Convert pyexasol result values into JSON-safe Ansible return values."""
    scalar = _json_safe_scalar(value)
    if scalar is not _JSON_SAFE_MISSING:
        return cast(JsonValue, scalar)

    if isinstance(value, Mapping):
        return {
            str(to_json_safe(key)): to_json_safe(item) for key, item in value.items()
        }

    if isinstance(value, (tuple, list)):
        return [to_json_safe(item) for item in value]

    return str(value)


def _json_safe_scalar(value: object) -> object:
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

    return _JSON_SAFE_MISSING


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
