"""Shared helpers for Exasol Ansible collection modules."""

from __future__ import annotations

import base64
import copy
import datetime as dt
import math
import re
import ssl
from collections.abc import (
    Iterable,
    Mapping,
    Sequence,
)
from decimal import Decimal
from typing import Any

DEFAULT_LOGIN_HOST = "localhost"
DEFAULT_LOGIN_PORT = 8563
DEFAULT_LOGIN_DB = ""
DEFAULT_AUTOCOMMIT = True
DEFAULT_FETCH_SIZE = 5000
DEFAULT_COMPRESSION = False
DEFAULT_ENCRYPTION = True
DEFAULT_VALIDATE_CERTS = True
REDACTED = "********"

CONNECTION_DEFAULTS: dict[str, Any] = {
    "login_host": DEFAULT_LOGIN_HOST,
    "login_port": DEFAULT_LOGIN_PORT,
    "login_db": DEFAULT_LOGIN_DB,
    "autocommit": DEFAULT_AUTOCOMMIT,
    "fetch_size": DEFAULT_FETCH_SIZE,
    "compression": DEFAULT_COMPRESSION,
    "encryption": DEFAULT_ENCRYPTION,
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
READ_ONLY_SQL_KEYWORDS = frozenset(
    {
        "DESCRIBE",
        "EXPLAIN",
        "SELECT",
        "SHOW",
        "VALUES",
        "WITH",
    }
)

_AUTHENTICATION_MARKERS = (
    "auth",
    "credential",
    "login",
    "password",
)
_NAMED_ARG_PATTERN = re.compile(r"[A-Za-z_]\w*", re.ASCII)


def exasol_connection_argument_spec() -> dict[str, dict[str, Any]]:
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
        "encryption": {"type": "bool", "default": DEFAULT_ENCRYPTION},
        "validate_certs": {"type": "bool", "default": DEFAULT_VALIDATE_CERTS},
        "ca_cert": {"type": "path"},
        "certificate_fingerprint": {"type": "str"},
        "client_kwargs": {"type": "dict", "default": {}, "no_log": True},
    }


def connection_parameters_with_defaults(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return connection parameters with shared defaults applied."""
    resolved = copy.deepcopy(CONNECTION_DEFAULTS)

    for name in CONNECTION_DEFAULTS:
        if name in params:
            resolved[name] = params[name]

    if "login_schema" in params and "login_db" not in params:
        resolved["login_db"] = params["login_schema"]

    for name in OPTIONAL_CONNECTION_PARAMETERS:
        if name in params:
            resolved[name] = params[name]

    return resolved


def build_exasol_dsn(params: Mapping[str, Any]) -> str:
    """Build a pyexasol DSN from Ansible connection parameters."""
    resolved = connection_parameters_with_defaults(params)
    host = resolved["login_host"]
    port = resolved["login_port"]
    fingerprint = resolved.get("certificate_fingerprint")

    if fingerprint:
        return f"{host}/{fingerprint}:{port}"

    return f"{host}:{port}"


def build_exasol_connect_kwargs(params: Mapping[str, Any]) -> dict[str, Any]:
    """Map connection parameters to pyexasol.connect keyword arguments."""
    resolved = connection_parameters_with_defaults(params)
    client_kwargs = dict(resolved.get("client_kwargs") or {})

    connect_kwargs = {
        "dsn": build_exasol_dsn(resolved),
        "user": resolved.get("login_user"),
        "password": resolved.get("login_password"),
        "schema": resolved.get("login_db") or "",
        "autocommit": resolved["autocommit"],
        "fetch_size_bytes": resolved["fetch_size"],
        "compression": resolved["compression"],
        "encryption": resolved["encryption"],
        "fetch_dict": True,
    }

    ca_cert = resolved.get("ca_cert")

    if (
        not resolved["validate_certs"]
        or resolved.get("certificate_fingerprint")
        or ca_cert
    ):
        websocket_sslopt = dict(client_kwargs.get("websocket_sslopt") or {})
        if ca_cert and resolved["validate_certs"]:
            websocket_sslopt["ca_certs"] = ca_cert
        websocket_sslopt["cert_reqs"] = (
            ssl.CERT_REQUIRED if resolved["validate_certs"] else ssl.CERT_NONE
        )
        connect_kwargs["websocket_sslopt"] = websocket_sslopt

    client_kwargs.update(connect_kwargs)
    return client_kwargs


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, Any],
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


def sanitize_error_message(error: Any, params: Mapping[str, Any]) -> str:
    """Redact known secret values from an error string."""
    message = str(error)

    for secret in _secret_values(params):
        message = message.replace(secret, REDACTED)

    return message


def normalize_query_list(query: Any) -> list[str]:
    """Normalize an Ansible query argument into an ordered statement list."""
    if isinstance(query, str):
        return [query]

    if isinstance(query, list) and all(isinstance(item, str) for item in query):
        return query

    raise ValueError("query must be a string or a list of strings.")


def execute_queries(
    connection: Any,
    query: str | list[str],
    positional_args: Sequence[Any] | None = None,
    named_args: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one or more Exasol statements and return Ansible result values."""
    queries = normalize_query_list(query)
    all_results = []
    rowcounts = []
    execution_time_ms = []

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
        "query_result": all_results[-1] if all_results else [],
        "query_all_results": all_results,
        "executed_queries": queries,
        "rowcount": rowcounts,
        "execution_time_ms": execution_time_ms,
    }


def prepare_query(
    query: str,
    positional_args: Sequence[Any] | None = None,
    named_args: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Translate Ansible-style placeholders into pyexasol formatter placeholders."""
    positional_values = list(positional_args or [])
    named_values = dict(named_args or {})
    query_params: dict[str, Any] = {}
    positional_index = 0
    rewritten = []
    index = 0

    while index < len(query):
        segment, index, positional_index = _prepare_query_segment(
            query=query,
            index=index,
            positional_values=positional_values,
            positional_index=positional_index,
            named_values=named_values,
            query_params=query_params,
        )
        rewritten.append(segment)

    if positional_index < len(positional_values):
        raise ValueError(
            "positional_args contains more values than query placeholders."
        )

    query_params.update(
        {
            name: _query_param_value(value)
            for name, value in named_values.items()
            if name not in query_params
        }
    )
    return "".join(rewritten), query_params


def _prepare_query_segment(
    query: str,
    index: int,
    positional_values: Sequence[Any],
    positional_index: int,
    named_values: Mapping[str, Any],
    query_params: dict[str, Any],
) -> tuple[str, int, int]:
    protected_segment_end = _protected_segment_end(query, index)
    if protected_segment_end is not None:
        return (
            query[index:protected_segment_end],
            protected_segment_end,
            positional_index,
        )

    character = query[index]
    if character == "?":
        return _prepare_positional_placeholder(
            index,
            positional_values,
            positional_index,
            query_params,
        )

    if character == ":":
        named_placeholder = _prepare_named_placeholder(
            query,
            index,
            named_values,
            query_params,
        )
        if named_placeholder is not None:
            segment, next_index = named_placeholder
            return segment, next_index, positional_index

    return character, index + 1, positional_index


def _protected_segment_end(query: str, index: int) -> int | None:
    if query.startswith("--", index):
        return _find_line_comment_end(query, index)

    if query.startswith("/*", index):
        return _find_block_comment_end(query, index)

    character = query[index]
    if character in ("'", '"'):
        return _find_quoted_string_end(query, index, quote=character)

    return None


def _prepare_positional_placeholder(
    index: int,
    positional_values: Sequence[Any],
    positional_index: int,
    query_params: dict[str, Any],
) -> tuple[str, int, int]:
    if positional_index >= len(positional_values):
        raise ValueError(
            "query contains more positional placeholders than positional_args values."
        )

    name = f"__pos_{positional_index}"
    value = positional_values[positional_index]
    query_params[name] = _query_param_value(value)
    return _pyexasol_placeholder(name, value), index + 1, positional_index + 1


def _prepare_named_placeholder(
    query: str,
    index: int,
    named_values: Mapping[str, Any],
    query_params: dict[str, Any],
) -> tuple[str, int] | None:
    if _is_double_colon(query, index):
        return None

    match = _NAMED_ARG_PATTERN.match(query, index + 1)
    if not match:
        return None

    name = match.group(0)
    if name not in named_values:
        return None

    value = named_values[name]
    query_params[name] = _query_param_value(value)
    return _pyexasol_placeholder(name, value), match.end()


def fetch_result_rows(statement: Any) -> list[Any]:
    """Fetch statement rows as JSON-safe dictionaries when rows are available."""
    if getattr(statement, "result_type", None) != "resultSet":
        return []

    rows = statement.fetchall()

    if rows and not isinstance(rows[0], Mapping):
        column_names = _statement_column_names(statement)
        rows = [dict(zip(column_names, row)) for row in rows]

    return rows_to_json_safe(rows)


def statement_rowcount(statement: Any) -> int:
    """Return a pyexasol statement rowcount as an integer."""
    rowcount = getattr(statement, "rowcount", 0)

    if callable(rowcount):
        rowcount = rowcount()

    return int(rowcount)


def statement_execution_time_ms(statement: Any) -> float:
    """Return pyexasol statement execution time in milliseconds."""
    return float(getattr(statement, "execution_time", 0) or 0) * 1000


def is_read_only_query(query: str) -> bool:
    """Return whether a SQL statement is conservatively considered read-only."""
    keyword = first_sql_keyword(query)

    return keyword in READ_ONLY_SQL_KEYWORDS


def first_sql_keyword(query: str) -> str:
    """Return the first SQL keyword after leading whitespace and comments."""
    index = 0

    while index < len(query):
        if query[index].isspace():
            index += 1
            continue

        if query.startswith("--", index):
            index = _find_line_comment_end(query, index)
            continue

        if query.startswith("/*", index):
            index = _find_block_comment_end(query, index)
            continue

        match = re.match(r"[A-Za-z]+", query[index:])
        if match:
            return match.group(0).upper()

        return ""

    return ""


def to_json_safe(value: Any) -> Any:
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


def rows_to_json_safe(rows: Iterable[Any]) -> list[Any]:
    """Convert Exasol result rows into JSON-safe values."""
    return [to_json_safe(row) for row in rows]


def _statement_column_names(statement: Any) -> list[str]:
    column_names = getattr(statement, "column_names", None)
    if callable(column_names):
        return list(column_names())

    return list(getattr(statement, "col_names", []))


def _secret_values(params: Mapping[str, Any]) -> set[str]:
    secrets = set()

    password = params.get("login_password")
    if isinstance(password, str) and password:
        secrets.add(password)

    client_kwargs = params.get("client_kwargs") or {}
    if isinstance(client_kwargs, Mapping):
        _collect_sensitive_values(client_kwargs, secrets)

    named_args = params.get("named_args") or {}
    if isinstance(named_args, Mapping):
        _collect_sensitive_values(named_args, secrets)

    return secrets


def _collect_sensitive_values(value: Any, secrets: set[str], key: str = "") -> None:
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


def _pyexasol_placeholder(name: str, value: Any) -> str:
    conversion = _pyexasol_conversion(value)
    if conversion:
        return f"{{{name}!{conversion}}}"

    return f"{{{name}}}"


def _pyexasol_conversion(value: Any) -> str:
    if isinstance(value, bool):
        return "r"

    if isinstance(value, int):
        return "d"

    if isinstance(value, Decimal):
        return "d"

    if isinstance(value, float):
        return "f"

    return ""


def _query_param_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    return value


def _find_line_comment_end(query: str, index: int) -> int:
    next_newline = query.find("\n", index)

    return len(query) if next_newline == -1 else next_newline


def _find_block_comment_end(query: str, index: int) -> int:
    comment_end = query.find("*/", index + 2)

    return len(query) if comment_end == -1 else comment_end + 2


def _find_quoted_string_end(query: str, index: int, quote: str) -> int:
    index += 1

    while index < len(query):
        if query[index] != quote:
            index += 1
            continue

        if index + 1 < len(query) and query[index + 1] == quote:
            index += 2
            continue

        return index + 1

    return len(query)


def _is_double_colon(query: str, index: int) -> bool:
    return (
        index + 1 < len(query)
        and query[index + 1] == ":"
        or index > 0
        and query[index - 1] == ":"
    )
