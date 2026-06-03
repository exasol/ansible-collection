"""Shared helpers for Exasol Ansible modules."""

from __future__ import annotations

import base64
import contextlib
import copy
import datetime as dt
import importlib
import math
import re
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
)
from decimal import Decimal
from typing import (
    Any,
    NoReturn,
)


def _fallback_missing_required_lib(library: str) -> str:
    """Return a fallback missing-library message outside Ansible runtime."""
    return (
        f"Failed to import the required Python library ({library}). "
        "Install it in the Ansible execution environment."
    )


try:
    missing_required_lib: Callable[[str], str] = getattr(
        importlib.import_module("ansible.module_utils.basic"),
        "missing_required_lib",
    )
except ImportError:
    missing_required_lib = _fallback_missing_required_lib


DEFAULT_LOGIN_HOST = "localhost"
DEFAULT_LOGIN_PORT = 8563
DEFAULT_ENCRYPTION = True
DEFAULT_AUTOCOMMIT = True
DEFAULT_COMPRESSION = False
MAX_IDENTIFIER_LENGTH = 128
REDACTED = "********"

EXASOL_CONNECTION_ARGUMENT_SPEC: dict[str, dict[str, Any]] = {
    "login_host": {
        "type": "str",
        "default": DEFAULT_LOGIN_HOST,
    },
    "login_port": {
        "type": "int",
        "default": DEFAULT_LOGIN_PORT,
    },
    "login_user": {
        "type": "str",
        "required": True,
    },
    "login_password": {
        "type": "str",
        "required": True,
        "no_log": True,
    },
    "login_db": {
        "type": "str",
        "default": "",
    },
    "autocommit": {
        "type": "bool",
        "default": DEFAULT_AUTOCOMMIT,
    },
    "fetch_size": {
        "type": "int",
        "required": False,
    },
    "compression": {
        "type": "bool",
        "default": DEFAULT_COMPRESSION,
    },
    "encryption": {
        "type": "bool",
        "default": DEFAULT_ENCRYPTION,
    },
    "client_kwargs": {
        "type": "dict",
        "default": {},
        "no_log": True,
    },
}

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

_REGULAR_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_AUTHENTICATION_MARKERS = (
    "auth",
    "credential",
    "login",
    "password",
)


class ExasolModuleError(RuntimeError):
    """Raised when an Exasol module helper fails after calling fail_json."""


def exasol_connection_argument_spec() -> dict[str, dict[str, Any]]:
    """Return a copy of the shared Exasol connection argument spec."""
    return copy.deepcopy(EXASOL_CONNECTION_ARGUMENT_SPEC)


def connection_parameters_with_defaults(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return connection parameters with shared defaults applied."""
    resolved: dict[str, Any] = {}

    for name, spec in EXASOL_CONNECTION_ARGUMENT_SPEC.items():
        if name in params:
            resolved[name] = params[name]
        elif "default" in spec:
            resolved[name] = copy.deepcopy(spec["default"])

    return resolved


def build_exasol_dsn(params: Mapping[str, Any]) -> str:
    """Build a pyexasol DSN from Ansible connection parameters."""
    resolved = connection_parameters_with_defaults(params)
    host = resolved["login_host"]
    port = resolved["login_port"]

    return f"{host}:{port}"


def build_exasol_connect_kwargs(params: Mapping[str, Any]) -> dict[str, Any]:
    """Map Ansible connection parameters to pyexasol.connect keyword arguments."""
    resolved = connection_parameters_with_defaults(params)
    client_kwargs = dict(resolved.get("client_kwargs") or {})

    connect_kwargs = {
        "dsn": build_exasol_dsn(resolved),
        "user": resolved.get("login_user"),
        "password": resolved.get("login_password"),
        "schema": resolved.get("login_db") or "",
        "autocommit": resolved["autocommit"],
        "compression": resolved["compression"],
        "encryption": resolved["encryption"],
    }

    if resolved.get("fetch_size") is not None:
        connect_kwargs["fetch_size_bytes"] = resolved["fetch_size"]

    client_kwargs.update(connect_kwargs)
    return client_kwargs


def import_pyexasol(module: Any) -> Any:
    """Import pyexasol or fail the Ansible module with a normalized message."""
    try:
        return importlib.import_module("pyexasol")
    except ImportError as error:
        message = missing_required_lib("pyexasol")
        module.fail_json(
            msg=message,
            exception=sanitize_error_message(error, getattr(module, "params", {})),
        )
        raise ExasolModuleError(message) from error


def connect_to_exasol(module: Any, pyexasol_module: Any | None = None) -> Any:
    """Open one pyexasol connection for the current module invocation."""
    pyexasol_module = pyexasol_module or import_pyexasol(module)
    connect_kwargs = build_exasol_connect_kwargs(module.params)

    try:
        return pyexasol_module.connect(**connect_kwargs)
    except Exception as error:
        fail_json_on_exasol_error(module, error, operation="Exasol connection")


@contextlib.contextmanager
def exasol_connection(module: Any, pyexasol_module: Any | None = None) -> Iterator[Any]:
    """Open and close one Exasol connection around a module operation."""
    connection = connect_to_exasol(module, pyexasol_module=pyexasol_module)

    try:
        yield connection
    finally:
        close = getattr(connection, "close", None)
        if close is not None:
            close()


def execute_exasol_statement(
    module: Any,
    connection: Any,
    statement: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a statement and normalize pyexasol execution errors."""
    try:
        return connection.execute(statement, *args, **kwargs)
    except Exception as error:
        fail_json_on_exasol_error(module, error, operation="Exasol statement execution")


def fail_json_on_exasol_error(
    module: Any,
    error: BaseException,
    operation: str = "Exasol operation",
) -> NoReturn:
    """Fail a module with a sanitized Exasol error message."""
    params = getattr(module, "params", {})
    safe_exception = sanitize_error_message(error, params)
    message = normalized_exasol_error_message(
        error,
        params=params,
        operation=operation,
    )

    module.fail_json(msg=message, exception=safe_exception)
    raise ExasolModuleError(message) from error


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


def validate_schema_name(name: str) -> str:
    """Validate an Exasol schema identifier."""
    return validate_identifier(name, identifier_type="schema")


def validate_user_name(name: str) -> str:
    """Validate an Exasol user identifier."""
    return validate_identifier(name, identifier_type="user")


def validate_role_name(name: str) -> str:
    """Validate an Exasol role identifier."""
    return validate_identifier(name, identifier_type="role")


def validate_object_name(name: str, allow_qualified: bool = True) -> str:
    """Validate an Exasol object identifier, optionally schema-qualified."""
    return validate_identifier(
        name,
        identifier_type="object",
        allow_qualified=allow_qualified,
    )


def validate_identifier(
    name: str,
    identifier_type: str = "identifier",
    allow_qualified: bool = False,
) -> str:
    """Validate a conservative Exasol regular identifier.

    Exasol supports more Unicode identifier characters than this helper accepts.
    Module parameters use this conservative subset to keep generated SQL
    predictable and avoid accidental dynamic-SQL injection.
    """
    if not isinstance(name, str):
        raise ValueError(f"Exasol {identifier_type} name must be a string.")

    parts = name.split(".") if allow_qualified else [name]
    if not parts or any(part == "" for part in parts):
        raise ValueError(f"Exasol {identifier_type} name must not be empty.")

    if allow_qualified and len(parts) > 2:
        raise ValueError(
            f"Exasol {identifier_type} name must use at most schema.object "
            "qualification."
        )

    for part in parts:
        _validate_identifier_part(part, identifier_type=identifier_type)

    return name


def quote_identifier(name: str, allow_qualified: bool = False) -> str:
    """Validate and quote an Exasol regular identifier using normal uppercase."""
    validate_identifier(name, allow_qualified=allow_qualified)
    parts = name.split(".") if allow_qualified else [name]

    return ".".join(f'"{part.upper()}"' for part in parts)


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


def _validate_identifier_part(part: str, identifier_type: str) -> None:
    if len(part) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"Exasol {identifier_type} identifier parts must not exceed "
            f"{MAX_IDENTIFIER_LENGTH} characters."
        )

    if not _REGULAR_IDENTIFIER_PATTERN.match(part):
        raise ValueError(
            f"Exasol {identifier_type} name '{part}' is not a valid regular "
            "identifier."
        )


def _secret_values(params: Mapping[str, Any]) -> set[str]:
    secrets = set()

    password = params.get("login_password")
    if isinstance(password, str) and password:
        secrets.add(password)

    client_kwargs = params.get("client_kwargs") or {}
    if isinstance(client_kwargs, Mapping):
        _collect_sensitive_values(client_kwargs, secrets)

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
