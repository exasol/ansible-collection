"""Tests for shared Exasol module utilities."""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from plugins.doc_fragments.exasol import ModuleDocFragment
from plugins.module_utils import exasol as exasol_utils


def test_connection_argument_spec_defines_defaults_and_no_log() -> None:
    """Verify shared connection options expose expected Ansible metadata."""
    spec = exasol_utils.exasol_connection_argument_spec()

    assert spec["login_host"]["default"] == "localhost"
    assert spec["login_port"]["default"] == 8563
    assert spec["encryption"]["default"] is True
    assert spec["login_password"]["no_log"] is True
    assert spec["client_kwargs"]["no_log"] is True


def test_build_exasol_connect_kwargs_maps_ansible_arguments_to_pyexasol() -> None:
    """Verify Ansible connection parameters map to pyexasol keyword arguments."""
    kwargs = exasol_utils.build_exasol_connect_kwargs(
        {
            "login_host": "db.example.com",
            "login_port": 8564,
            "login_user": "sys",
            "login_password": "secret",
            "login_db": "APP",
            "autocommit": False,
            "fetch_size": 1024,
            "compression": True,
            "encryption": False,
            "client_kwargs": {
                "client_name": "ansible-test",
                "encryption": True,
            },
        }
    )

    assert kwargs == {
        "dsn": "db.example.com:8564",
        "user": "sys",
        "password": "secret",
        "schema": "APP",
        "autocommit": False,
        "fetch_size_bytes": 1024,
        "compression": True,
        "encryption": False,
        "client_name": "ansible-test",
    }


def test_build_exasol_connect_kwargs_applies_defaults() -> None:
    """Verify default connection handling, including TLS by default."""
    kwargs = exasol_utils.build_exasol_connect_kwargs(
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


def test_import_pyexasol_failure_uses_missing_required_lib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify pyexasol import failures use a clear Ansible dependency failure."""
    module = _module({"login_password": "secret"})

    def fail_import(name: str) -> object:
        assert name == "pyexasol"
        raise ImportError("No module named pyexasol")

    monkeypatch.setattr(exasol_utils.importlib, "import_module", fail_import)

    with pytest.raises(exasol_utils.ExasolModuleError):
        exasol_utils.import_pyexasol(module)

    module.fail_json.assert_called_once()
    fail_kwargs = module.fail_json.call_args.kwargs
    assert "pyexasol" in fail_kwargs["msg"]
    assert "No module named pyexasol" in fail_kwargs["exception"]


def test_connect_to_exasol_opens_one_pyexasol_connection() -> None:
    """Verify connection helper opens a pyexasol connection with mapped kwargs."""
    module = _module(
        {
            "login_host": "db.example.com",
            "login_port": 8563,
            "login_user": "sys",
            "login_password": "secret",
        }
    )
    connection = object()
    pyexasol_module = SimpleNamespace(connect=Mock(return_value=connection))

    result = exasol_utils.connect_to_exasol(module, pyexasol_module=pyexasol_module)

    assert result is connection
    pyexasol_module.connect.assert_called_once_with(
        dsn="db.example.com:8563",
        user="sys",
        password="secret",
        schema="",
        autocommit=True,
        compression=False,
        encryption=True,
    )


def test_exasol_connection_context_closes_connection() -> None:
    """Verify the context manager closes each per-invocation connection."""
    module = _module({"login_user": "sys", "login_password": "secret"})
    connection = SimpleNamespace(close=Mock())
    pyexasol_module = SimpleNamespace(connect=Mock(return_value=connection))

    with exasol_utils.exasol_connection(
        module,
        pyexasol_module=pyexasol_module,
    ) as active_connection:
        assert active_connection is connection

    connection.close.assert_called_once_with()


def test_authentication_error_is_sanitized() -> None:
    """Verify failed authentication does not expose passwords or tokens."""
    module = _module(
        {
            "login_user": "sys",
            "login_password": "swordfish",
            "client_kwargs": {"custom_api_token": "token-value"},
        }
    )
    pyexasol_module = SimpleNamespace(
        connect=Mock(
            side_effect=RuntimeError(
                "authentication failed for password swordfish and token token-value"
            )
        )
    )

    with pytest.raises(exasol_utils.ExasolModuleError):
        exasol_utils.connect_to_exasol(module, pyexasol_module=pyexasol_module)

    fail_kwargs = module.fail_json.call_args.kwargs
    assert "authenticate" in fail_kwargs["msg"]
    assert "swordfish" not in fail_kwargs["msg"]
    assert "swordfish" not in fail_kwargs["exception"]
    assert "token-value" not in fail_kwargs["exception"]


def test_execution_error_is_sanitized() -> None:
    """Verify statement execution errors are normalized and redacted."""
    module = _module({"login_password": "swordfish"})
    connection = SimpleNamespace(
        execute=Mock(side_effect=RuntimeError("SQL failed near swordfish"))
    )

    with pytest.raises(exasol_utils.ExasolModuleError):
        exasol_utils.execute_exasol_statement(module, connection, "select 1")

    fail_kwargs = module.fail_json.call_args.kwargs
    assert fail_kwargs["msg"] == (
        "Exasol statement execution failed: SQL failed near ********"
    )
    assert fail_kwargs["exception"] == "SQL failed near ********"


def test_identifier_validation_helpers_accept_regular_identifiers() -> None:
    """Verify schema, user, role, and object identifier helpers."""
    assert exasol_utils.validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"
    assert exasol_utils.validate_user_name("APP_USER1") == "APP_USER1"
    assert exasol_utils.validate_role_name("APP_ROLE") == "APP_ROLE"
    assert exasol_utils.validate_object_name("APP_SCHEMA.TABLE1") == "APP_SCHEMA.TABLE1"
    assert exasol_utils.quote_identifier("app_schema.table1", allow_qualified=True) == (
        '"APP_SCHEMA"."TABLE1"'
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "1APP",
        "APP-TABLE",
        "APP TABLE",
        "APP.TABLE.EXTRA",
        f"A{'B' * 128}",
    ],
)
def test_identifier_validation_helpers_reject_invalid_schema_names(name: str) -> None:
    """Verify invalid identifiers are rejected before dynamic SQL generation."""
    with pytest.raises(ValueError):
        exasol_utils.validate_schema_name(name)


def test_object_identifier_validation_rejects_too_many_parts() -> None:
    """Verify object names are limited to schema.object qualification."""
    with pytest.raises(ValueError):
        exasol_utils.validate_object_name("APP.TABLE.EXTRA")


def test_to_json_safe_converts_exasol_values() -> None:
    """Verify Exasol result values can be serialized as JSON."""
    converted = exasol_utils.to_json_safe(
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
    assert "pyexasol" in documentation


def _module(params: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(params=params, fail_json=Mock())
