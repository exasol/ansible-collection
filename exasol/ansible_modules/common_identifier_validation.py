"""Centralized Exasol identifier validation and quoting utilities."""

from __future__ import annotations

import re

MAX_IDENTIFIER_LENGTH = 128

_REGULAR_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z]\w*$",
    re.ASCII,
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
            f"Exasol {identifier_type} name must use at most "
            "schema.object qualification."
        )

    for part in parts:
        _validate_identifier_part(part, identifier_type)

    return name


def quote_identifier(name: str, allow_qualified: bool = False) -> str:
    """Validate and quote an identifier using uppercase SQL rules."""

    validate_identifier(name, allow_qualified=allow_qualified)

    parts = name.split(".") if allow_qualified else [name]

    return ".".join(f'"{part.upper()}"' for part in parts)


# ---- specialized wrappers (thin, consistent API surface) ----


def validate_user_name(name: str) -> str:
    """Validate an Exasol user identifier."""
    return validate_identifier(name, identifier_type="user")


def validate_role_name(name: str) -> str:
    """Validate an Exasol role identifier."""
    return validate_identifier(name, identifier_type="role")


def validate_schema_name(name: str) -> str:
    """Validate an Exasol schema identifier."""
    return validate_identifier(name, identifier_type="schema")


def validate_object_name(name: str, allow_qualified: bool = True) -> str:
    """Validate an Exasol object identifier, optionally schema-qualified."""
    return validate_identifier(
        name,
        identifier_type="object",
        allow_qualified=allow_qualified,
    )


# ---- internal helper ----


def _validate_identifier_part(part: str, identifier_type: str) -> None:
    if len(part) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"Exasol {identifier_type} identifier parts must not exceed "
            f"{MAX_IDENTIFIER_LENGTH} characters."
        )

    if not _REGULAR_IDENTIFIER_PATTERN.match(part):
        raise ValueError(
            f"Exasol {identifier_type} name '{part}' is not a valid regular identifier."
        )
