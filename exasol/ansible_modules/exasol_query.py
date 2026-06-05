"""Reusable Exasol query logic independent from Ansible runtime APIs."""

from __future__ import annotations

import base64
import copy
import datetime as dt
import math
import ssl
from collections.abc import (
    Iterable,
    Mapping,
)
from decimal import Decimal
from typing import Any

DEFAULT_LOGIN_HOST = "localhost"
DEFAULT_LOGIN_PORT = 8563
DEFAULT_AUTOCOMMIT = True
DEFAULT_COMPRESSION = False
DEFAULT_VALIDATE_CERTS = True
REDACTED = "********"

CONNECTION_DEFAULTS: dict[str, Any] = {
    "login_host": DEFAULT_LOGIN_HOST,
    "login_port": DEFAULT_LOGIN_PORT,
    "login_schema": "",
    "autocommit": DEFAULT_AUTOCOMMIT,
    "compression": DEFAULT_COMPRESSION,
    "validate_certs": DEFAULT_VALIDATE_CERTS,
    "client_kwargs": {},
}
OPTIONAL_CONNECTION_PARAMETERS = (
    "login_user",
    "login_password",
    "fetch_size",
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

_AUTHENTICATION_MARKERS = (
    "auth",
    "credential",
    "login",
    "password",
)


def connection_parameters_with_defaults(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return connection parameters with shared defaults applied."""
    resolved = copy.deepcopy(CONNECTION_DEFAULTS)

    for name in CONNECTION_DEFAULTS:
        if name in params:
            resolved[name] = params[name]

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
        "schema": resolved.get("login_schema") or "",
        "autocommit": resolved["autocommit"],
        "compression": resolved["compression"],
        "encryption": True,
    }

    if resolved.get("fetch_size") is not None:
        connect_kwargs["fetch_size_bytes"] = resolved["fetch_size"]

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
