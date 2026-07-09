"""Tests for shared runtime validation helpers."""

from __future__ import annotations

import pytest

from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier,
    quote_identifier,
    validate_identifier,
    validate_object_name,
    validate_role_name,
    validate_schema_name,
    validate_user_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)


def test_choice_string_accepts_valid_values() -> None:
    """Verify choice string options are returned after validation."""
    assert (
        validate_choice_param(
            {"state": "absent"},
            "state",
            "present",
            {"present", "absent"},
        )
        == "absent"
    )


def test_choice_string_uses_default_value() -> None:
    """Verify missing choice string options use the provided default."""
    assert (
        validate_choice_param({}, "state", "present", {"present", "absent"})
        == "present"
    )


def test_choice_string_rejects_invalid_values() -> None:
    """Verify invalid choice values fail with an actionable message."""
    with pytest.raises(ValueError, match="state must be one of"):
        validate_choice_param(
            {"state": "invalid"},
            "state",
            "present",
            {"present", "absent"},
        )


def test_required_string_accepts_non_empty_string() -> None:
    """Verify required string options are returned after validation."""
    assert validate_required_param({"name": "app_user"}, "name") == "app_user"


@pytest.mark.parametrize("value", [None, "", object()])
def test_required_string_rejects_invalid_values(value: object) -> None:
    """Verify required string options must be non-empty strings."""
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        validate_required_param({"name": value}, "name")


def test_identifier_validation_helpers_accept_regular_identifiers() -> None:
    """Verify schema, user, role, and object identifier helpers."""
    assert validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"
    assert validate_user_name("App+/=User") == "App+/=User"
    assert validate_user_name('"App+/=User"') == "App+/=User"
    assert validate_role_name("App+/=Role") == "App+/=Role"
    assert validate_role_name('"App+/=Role"') == "App+/=Role"
    assert validate_object_name("APP_SCHEMA.TABLE1") == "APP_SCHEMA.TABLE1"
    assert quote_exact_identifier('ab"c', identifier_type="user") == '"ab""c"'
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


def test_validate_identifier_rejects_names_not_matching_regular_pattern() -> None:
    """Verify identifiers must match the conservative regular identifier pattern."""
    with pytest.raises(ValueError, match="not a valid regular identifier"):
        validate_schema_name("APP-SCHEMA")


@pytest.mark.parametrize("name", ['"unterminated', '"bad"quote"'])
def test_validate_user_name_rejects_malformed_delimited_syntax(name: str) -> None:
    """Verify malformed quoted user identifiers fail with a clear error."""
    with pytest.raises(ValueError, match="malformed delimited identifier syntax"):
        validate_user_name(name)


def test_object_identifier_validation_rejects_too_many_parts() -> None:
    """Verify object names are limited to schema.object qualification."""
    with pytest.raises(ValueError):
        validate_object_name("APP.TABLE.EXTRA")


@pytest.mark.parametrize("identifier", [object(), ""])
def test_validate_identifier_rejects_invalid_name_types(identifier: object) -> None:
    """Verify identifier validation rejects non-string and empty values directly."""
    with pytest.raises(ValueError):
        validate_identifier(identifier)  # type: ignore[arg-type]
