"""Centralized Exasol identifier validation and quoting utilities."""

from __future__ import annotations

import re

MAX_IDENTIFIER_LENGTH = 128

_REGULAR_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z]\w{0,127}$",
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
            f"Exasol {identifier_type} identifier must either be "
            "'<object-name>' or '<schema-name>.<object-name>'."
        )

    for part in parts:
        _validate_identifier_part(part, identifier_type)

    return name


def quote_identifier(name: str, allow_qualified: bool = False) -> str:
    """Validate and quote an identifier using uppercase SQL rules."""

    validate_identifier(name, allow_qualified=allow_qualified)

    parts = name.split(".") if allow_qualified else [name]

    return ".".join(f'"{part.upper()}"' for part in parts)


def validate_exact_identifier(
    name: str,
    identifier_type: str = "identifier",
) -> str:
    """Validate an exact identifier value or delimited SQL identifier syntax."""
    if not isinstance(name, str):
        raise ValueError(f"Exasol {identifier_type} name must be a string.")

    if name == "":
        raise ValueError(f"Exasol {identifier_type} name must not be empty.")

    value = _exact_identifier_value(name, identifier_type)

    if value == "":
        raise ValueError(f"Exasol {identifier_type} name must not be empty.")

    if "\x00" in value:
        raise ValueError(
            f"Exasol {identifier_type} name must not contain NUL characters."
        )

    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"Exasol {identifier_type} identifier parts must not exceed "
            f"{MAX_IDENTIFIER_LENGTH} characters."
        )

    return value


def quote_exact_identifier(name: str, identifier_type: str = "identifier") -> str:
    """Quote an exact identifier value without uppercasing it."""
    value = validate_exact_identifier(name, identifier_type=identifier_type)
    escaped_value = value.replace('"', '""')
    return f'"{escaped_value}"'


# ---- specialized wrappers (thin, consistent API surface) ----


def validate_user_name(name: str) -> str:
    """Validate an exact Exasol user identifier."""
    return validate_exact_identifier(name, identifier_type="user")


def validate_role_name(name: str) -> str:
    """Validate an exact Exasol role identifier."""
    return validate_exact_identifier(name, identifier_type="role")


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


def _exact_identifier_value(name: str, identifier_type: str) -> str:
    if not name.startswith('"'):
        if name.endswith('"'):
            raise ValueError(
                f"Exasol {identifier_type} name uses malformed delimited identifier "
                "syntax."
            )
        return name

    if not name.endswith('"') or len(name) < 2:
        raise ValueError(
            f"Exasol {identifier_type} name uses malformed delimited identifier "
            "syntax."
        )

    value: list[str] = []
    inner = name[1:-1]
    index = 0
    while index < len(inner):
        char = inner[index]
        if char != '"':
            value.append(char)
            index += 1
            continue

        if index + 1 >= len(inner) or inner[index + 1] != '"':
            raise ValueError(
                f"Exasol {identifier_type} name uses malformed delimited identifier "
                "syntax."
            )

        value.append('"')
        index += 2

    return "".join(value)
