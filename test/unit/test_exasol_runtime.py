"""Tests for the Exasol Ansible runtime package."""

from __future__ import annotations

import datetime as dt
import json
import ssl
from decimal import Decimal

import pytest

from exasol.ansible_modules import (
    exasol_query,
    exasol_user,
)
from plugins.doc_fragments.exasol import ModuleDocFragment


def test_build_exasol_connect_kwargs_maps_ansible_arguments_to_pyexasol() -> None:
    """Verify Ansible connection parameters map to pyexasol keyword arguments."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_host": "db.example.com",
            "login_port": 8564,
            "login_user": "sys",
            "login_password": "secret",
            "login_schema": "APP",
            "autocommit": False,
            "fetch_size": 1024,
            "compression": True,
            "validate_certs": False,
            "certificate_fingerprint": "ABCDEF",
            "client_kwargs": {
                "client_name": "ansible-test",
                "encryption": False,
                "websocket_sslopt": {"check_hostname": False},
            },
        }
    )

    assert kwargs == {
        "dsn": "db.example.com/ABCDEF:8564",
        "user": "sys",
        "password": "secret",
        "schema": "APP",
        "autocommit": False,
        "fetch_size_bytes": 1024,
        "compression": True,
        "encryption": True,
        "websocket_sslopt": {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False,
        },
        "client_name": "ansible-test",
    }


def test_build_exasol_connect_kwargs_applies_defaults() -> None:
    """Verify default connection handling, including mandatory TLS."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
        }
    )

    assert kwargs["dsn"] == "localhost:8563"
    assert kwargs["schema"] == ""
    assert kwargs["autocommit"] is True
    assert kwargs["compression"] is False
    assert kwargs["encryption"] is True
    assert "fetch_size_bytes" not in kwargs
    assert "websocket_sslopt" not in kwargs


def test_build_exasol_connect_kwargs_keeps_ca_validation_with_fingerprint() -> None:
    """Verify fingerprints pin the certificate without disabling CA validation."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_host": "db.example.com",
            "login_user": "sys",
            "login_password": "secret",
            "certificate_fingerprint": "ABCDEF",
        }
    )

    assert kwargs["dsn"] == "db.example.com/ABCDEF:8563"
    assert kwargs["encryption"] is True
    assert kwargs["websocket_sslopt"] == {"cert_reqs": ssl.CERT_REQUIRED}


def test_authentication_error_is_sanitized() -> None:
    """Verify failed authentication does not expose passwords or tokens."""
    params = {
        "login_user": "sys",
        "login_password": "swordfish",
        "client_kwargs": {"custom_api_token": "token-value"},
    }
    message = exasol_query.normalized_exasol_error_message(
        RuntimeError(
            "authentication failed for password swordfish and token token-value"
        ),
        params=params,
        operation="Exasol connection",
    )
    exception = exasol_query.sanitize_error_message(
        RuntimeError(
            "authentication failed for password swordfish and token token-value"
        ),
        params,
    )

    assert "authenticate" in message
    assert "swordfish" not in message
    assert "swordfish" not in exception
    assert "token-value" not in exception


def test_execution_error_is_sanitized() -> None:
    """Verify statement execution errors are normalized and redacted."""
    params = {"login_password": "swordfish"}

    message = exasol_query.normalized_exasol_error_message(
        RuntimeError("SQL failed near swordfish"),
        params=params,
        operation="Exasol statement execution",
    )
    exception = exasol_query.sanitize_error_message(
        RuntimeError("SQL failed near swordfish"),
        {
            "login_password": "swordfish",
        },
    )

    assert message == ("Exasol statement execution failed: SQL failed near ********")
    assert exception == "SQL failed near ********"


def test_identifier_validation_helpers_accept_regular_identifiers() -> None:
    """Verify schema, user, role, and object identifier helpers."""
    assert exasol_user.validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"
    assert exasol_user.validate_user_name("APP_USER1") == "APP_USER1"
    assert exasol_user.validate_role_name("APP_ROLE") == "APP_ROLE"
    assert exasol_user.validate_object_name("APP_SCHEMA.TABLE1") == (
        "APP_SCHEMA.TABLE1"
    )
    assert (
        exasol_user.quote_identifier(
            "app_schema.table1",
            allow_qualified=True,
        )
        == '"APP_SCHEMA"."TABLE1"'
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "1APP",
        "APP-TABLE",
        "APP TABLE",
        "APPÄ",
        "APP.TABLE.EXTRA",
        f"A{'B' * 128}",
    ],
)
def test_identifier_validation_helpers_reject_invalid_schema_names(name: str) -> None:
    """Verify invalid identifiers are rejected before dynamic SQL generation."""
    with pytest.raises(ValueError):
        exasol_user.validate_schema_name(name)


def test_object_identifier_validation_rejects_too_many_parts() -> None:
    """Verify object names are limited to schema.object qualification."""
    with pytest.raises(ValueError):
        exasol_user.validate_object_name("APP.TABLE.EXTRA")


def test_to_json_safe_converts_exasol_values() -> None:
    """Verify Exasol result values can be serialized as JSON."""
    converted = exasol_query.to_json_safe(
        {
            "amount": Decimal("12.30"),
            "created_on": dt.date(2026, 1, 2),
            "created_at": dt.datetime(2026, 1, 2, 3, 4, 5),
            "payload": b"\x01\x02",
            "rows": [(Decimal("1.5"), dt.time(3, 4, 5))],
            "not_a_number": float("nan"),
        }
    )

    json.dumps(converted)

    assert converted == {
        "amount": "12.30",
        "created_on": "2026-01-02",
        "created_at": "2026-01-02T03:04:05",
        "payload": "AQI=",
        "rows": [["1.5", "03:04:05"]],
        "not_a_number": "nan",
    }


def test_doc_fragment_exposes_connection_options() -> None:
    """Verify modules can reuse the Exasol connection documentation fragment."""
    documentation = ModuleDocFragment.DOCUMENTATION

    assert "login_host" in documentation
    assert "login_password" in documentation
    assert "exasol-ansible-modules" in documentation
