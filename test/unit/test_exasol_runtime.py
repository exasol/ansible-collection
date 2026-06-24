"""Tests for the Exasol Ansible runtime package."""

from __future__ import annotations

import builtins
import datetime as dt
import importlib.util
import json
import ssl
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from exasol.ansible_modules import (
    exasol_query,
)
from exasol.ansible_modules.common_identifier_validation import (
    quote_identifier,
    validate_object_name,
    validate_role_name,
    validate_schema_name,
    validate_user_name,
)
from plugins.doc_fragments.exasol_query import ModuleDocFragment


def test_runtime_argument_spec_import_does_not_require_sqlglot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sanity-test argument spec introspection does not need SQL parsing deps."""
    runtime_path = Path(exasol_query.__file__).resolve()
    original_import = builtins.__import__

    def import_without_sqlglot(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "sqlglot" or name.startswith("sqlglot."):
            raise ImportError("blocked sqlglot import")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_sqlglot)
    spec = importlib.util.spec_from_file_location(
        "_exasol_query_without_sqlglot",
        runtime_path,
    )

    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.exasol_connection_argument_spec()["login_password"]["no_log"] is True


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
        "fetch_dict": True,
        "websocket_sslopt": {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False,
        },
        "client_name": "ansible-test",
    }


def test_connection_argument_spec_does_not_expose_encryption_option() -> None:
    """Verify TLS cannot be disabled through the public module interface."""
    assert "encryption" not in exasol_query.exasol_connection_argument_spec()


def test_build_exasol_connect_kwargs_forces_tls() -> None:
    """Verify legacy or client kwargs cannot disable TLS."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "encryption": False,
            "client_kwargs": {"encryption": False},
        }
    )

    assert kwargs["encryption"] is True


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
    assert kwargs["fetch_size_bytes"] == 5000
    assert kwargs["fetch_dict"] is True
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


def test_build_exasol_connect_kwargs_keeps_default_ssl_validation() -> None:
    """Verify validation without custom trust material uses pyexasol defaults."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "validate_certs": True,
        }
    )

    assert "websocket_sslopt" not in kwargs


def test_build_exasol_connect_kwargs_disables_ssl_validation_without_ca_cert() -> None:
    """Verify validation can be disabled without providing CA certificates."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "validate_certs": False,
        }
    )

    assert kwargs["websocket_sslopt"] == {"cert_reqs": ssl.CERT_NONE}


def test_build_exasol_connect_kwargs_merges_ca_cert_ssl_options() -> None:
    """Verify CA certificate handling preserves custom WebSocket SSL options."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_host": "db.example.com",
            "login_user": "sys",
            "login_password": "secret",
            "ca_cert": "/etc/exasol/ca.pem",
            "client_kwargs": {
                "websocket_sslopt": {"check_hostname": True},
            },
        }
    )

    assert kwargs["dsn"] == "db.example.com:8563"
    assert kwargs["websocket_sslopt"] == {
        "ca_certs": "/etc/exasol/ca.pem",
        "cert_reqs": ssl.CERT_REQUIRED,
        "check_hostname": True,
    }


def test_build_exasol_connect_kwargs_uses_ca_cert_with_validation() -> None:
    """Verify CA certificates are passed through when validation is enabled."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "validate_certs": True,
            "ca_cert": "/etc/exasol/ca.pem",
        }
    )

    assert kwargs["websocket_sslopt"] == {
        "ca_certs": "/etc/exasol/ca.pem",
        "cert_reqs": ssl.CERT_REQUIRED,
    }


def test_build_exasol_connect_kwargs_uses_ca_cert_with_default_validation() -> None:
    """Verify certificate validation is enabled by default for CA certificates."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "ca_cert": "/etc/exasol/ca.pem",
        }
    )

    assert kwargs["websocket_sslopt"] == {
        "ca_certs": "/etc/exasol/ca.pem",
        "cert_reqs": ssl.CERT_REQUIRED,
    }


def test_build_exasol_connect_kwargs_ignores_ca_cert_without_validation() -> None:
    """Verify CA certificates are ignored when TLS validation is disabled."""
    kwargs = exasol_query.build_exasol_connect_kwargs(
        {
            "login_user": "sys",
            "login_password": "secret",
            "validate_certs": False,
            "ca_cert": "/etc/exasol/ca.pem",
        }
    )

    assert kwargs["websocket_sslopt"] == {"cert_reqs": ssl.CERT_NONE}


@pytest.mark.parametrize("query", [2, ["SELECT 1", 2]])
def test_normalize_query_list_rejects_invalid_query(query: object) -> None:
    """Verify query parameters must be a string or list of strings."""
    with pytest.raises(ValueError, match="query must be"):
        exasol_query.normalize_query_list(query)


def test_last_available_query_result_returns_last_statement_rows() -> None:
    """Verify the public query_result mirrors the last executed statement."""
    assert exasol_query.last_available_query_result([]) == []
    assert exasol_query.last_available_query_result(
        [
            [{"FIRST": 1}],
            [{"LAST": 2}],
        ]
    ) == [{"LAST": 2}]


def test_prepare_query_handles_comments_quotes_and_parameter_types() -> None:
    """Verify placeholder parsing ignores comments and quoted literals."""
    query, query_params = exasol_query.prepare_query(
        "\n"
        "-- ? :ignored\n"
        "/* ? :ignored */\n"
        "SELECT \"?\" AS Q, '?' AS S, ? AS B, -- ? :inline_ignored\n"
        "? AS D, ? AS F, :name AS N",
        positional_args=[True, Decimal("12.3"), 1.5],
        named_args={"name": "Alice"},
    )

    assert query == (
        "\n"
        "-- ? :ignored\n"
        "/* ? :ignored */\n"
        "SELECT \"?\" AS Q, '?' AS S, {__pos_0!r} AS B, -- ? :inline_ignored\n"
        "{__pos_1!d} AS D, {__pos_2!f} AS F, {name} AS N"
    )
    assert query_params == {
        "__pos_0": "TRUE",
        "__pos_1": Decimal("12.3"),
        "__pos_2": 1.5,
        "name": "Alice",
    }


def test_prepare_query_rejects_missing_positional_argument() -> None:
    """Verify each positional placeholder must have a value."""
    with pytest.raises(ValueError) as error_info:
        exasol_query.prepare_query("SELECT ? AS A")

    message = str(error_info.value)
    assert "positional_args does not match" in message
    assert "query contains 1 '?' placeholder(s)" in message
    assert "positional_args contains 0 value(s)" in message
    assert "Add a value for each '?'" in message


def test_prepare_query_rejects_extra_positional_argument() -> None:
    """Verify unused positional values are rejected."""
    with pytest.raises(ValueError) as error_info:
        exasol_query.prepare_query("SELECT 1 AS A", positional_args=[1])

    message = str(error_info.value)
    assert "positional_args does not match" in message
    assert "query contains 0 '?' placeholder(s)" in message
    assert "positional_args contains 1 value(s)" in message
    assert "remove the extra positional_args entries" in message


def test_prepare_query_rejects_missing_named_argument() -> None:
    """Verify each named placeholder must have a value."""
    with pytest.raises(ValueError) as error_info:
        exasol_query.prepare_query("SELECT :missing_value AS A")

    message = str(error_info.value)
    assert "named_args does not match" in message
    assert "query contains named placeholder ':missing_value'" in message
    assert "named_args does not contain a value" in message


def test_prepare_query_rejects_extra_named_argument() -> None:
    """Verify unused named values are rejected."""
    with pytest.raises(ValueError) as error_info:
        exasol_query.prepare_query(
            "SELECT :used_value AS A",
            named_args={"used_value": 17, "unused_value": 19},
        )

    message = str(error_info.value)
    assert "named_args contains unused value(s)" in message
    assert "unused_value" in message
    assert "remove the extra named_args entries" in message


def test_is_read_only_query_classifies_common_sql_statements() -> None:
    """Verify read-only detection handles common Exasol SQL statement types."""
    assert (
        exasol_query.is_read_only_query(" \n -- comment\n /* block */ SELECT 1") is True
    )
    assert exasol_query.is_read_only_query("  ;") is False
    assert exasol_query.is_read_only_query("  ") is False
    assert exasol_query.is_read_only_query("VALUES 1") is True
    assert exasol_query.is_read_only_query("SHOW TABLES") is True
    assert exasol_query.is_read_only_query("EXPLAIN SELECT 1") is True
    assert exasol_query.is_read_only_query("DESCRIBE TABLE T") is True
    assert exasol_query.is_read_only_query("DESC TABLE T") is False
    assert (
        exasol_query.is_read_only_query("WITH q AS (SELECT 1) SELECT * FROM q") is True
    )
    assert exasol_query.is_read_only_query("SELECT 1 INTO T") is False
    assert (
        exasol_query.is_read_only_query(
            "WITH q AS (SELECT 1) INSERT INTO T SELECT * FROM q"
        )
        is False
    )
    assert exasol_query.is_read_only_query("GRANT SELECT ON T TO U") is False
    assert exasol_query.is_read_only_query("INSERT INTO T VALUES 1") is False
    assert exasol_query.is_read_only_query("TRUNCATE TABLE T") is False
    assert exasol_query.is_read_only_query("CALL F()") is False


def test_is_read_only_query_parse_error_fallback_is_conservative_for_select(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify parser failures do not classify SELECT statements as read-only."""

    class ParserFailure(Exception):
        pass

    class Parser:
        def parse(self, _query: str, *, read: str) -> list[object]:
            raise ParserFailure()

    monkeypatch.setattr(
        exasol_query,
        "_sqlglot_parser_runtime",
        lambda: (Parser(), object(), (ParserFailure,)),
    )

    assert exasol_query.is_read_only_query("SELECT 1") is False
    assert exasol_query.is_read_only_query("SHOW TABLES") is True


def test_fetch_result_rows_uses_col_names_fallback() -> None:
    """Verify tuple rows can use the pyexasol col_names attribute."""

    class StatementWithoutColumnMethod:
        result_type = "resultSet"
        col_names = ["A", "B"]

        def fetchall(self) -> list[tuple[int, str]]:
            return [(1, "x")]

    assert exasol_query.fetch_result_rows(StatementWithoutColumnMethod()) == [
        {"A": 1, "B": "x"}
    ]


def test_statement_metadata_reads_pyexasol_rowcount_method() -> None:
    """Verify statement row count metadata uses pyexasol's rowcount method."""

    class Statement:
        def rowcount(self) -> int:
            return 3

    statement = Statement()

    assert exasol_query.statement_rowcount(statement) == 3


def test_statement_execution_time_defaults_to_zero() -> None:
    """Verify missing pyexasol execution time metadata defaults to zero."""

    class Statement:
        pass

    statement = Statement()

    assert exasol_query.statement_execution_time_ms(statement) == 0.0


def test_sanitize_error_message_redacts_nested_sensitive_values() -> None:
    """Verify nested secret values are redacted from client kwargs."""
    message = exasol_query.sanitize_error_message(
        RuntimeError("secret-one token-two public"),
        {
            "client_kwargs": {
                "nested": [
                    {"client_secret": "secret-one"},
                ],
                "token": ("token-two",),
                "plain": "public",
            }
        },
    )

    assert message == "******** ******** public"


def test_sanitize_error_message_redacts_overlapping_secrets() -> None:
    """Verify shorter secret values cannot expose suffixes of longer secrets."""
    message = exasol_query.sanitize_error_message(
        RuntimeError("token abcdef password abc"),
        {
            "login_password": "abc",
            "named_args": {"api_token": "abcdef"},
        },
    )

    assert message == "token ******** password ********"


def test_to_json_safe_converts_unknown_objects_to_strings() -> None:
    """Verify unsupported values still become JSON-serializable."""

    class CustomValue:
        def __str__(self) -> str:
            return "custom-value"

    assert exasol_query.to_json_safe(CustomValue()) == "custom-value"


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
    assert validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"
    assert validate_user_name("APP_USER1") == "APP_USER1"
    assert validate_role_name("APP_ROLE") == "APP_ROLE"
    assert validate_object_name("APP_SCHEMA.TABLE1") == "APP_SCHEMA.TABLE1"
    assert (
        quote_identifier(
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
        validate_schema_name(name)


def test_object_identifier_validation_rejects_too_many_parts() -> None:
    """Verify object names are limited to schema.object qualification."""
    with pytest.raises(ValueError):
        validate_object_name("APP.TABLE.EXTRA")


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
    assert "ca_cert" in documentation
    assert "  encryption:" not in documentation
    assert "exasol-ansible-modules" in documentation
