"""Reusable Exasol schema lifecycle logic, shared by exasol_init.

Extracted as a standalone module in the same shape as common_role.py and
common_user.py so a future standalone exasol_schema module (see
doc/system_requirements.md) can wrap it without duplicating logic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    quote_identifier,
    validate_schema_name,
    validate_user_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

DEFAULT_STATE = "present"
DEFAULT_CASCADE = False

SCHEMA_METADATA_QUERY = """
SELECT SCHEMA_NAME, SCHEMA_OWNER
FROM EXA_ALL_SCHEMAS
WHERE UPPER(SCHEMA_NAME) = UPPER(:schema_name)
"""

STATES = frozenset({"present", "absent"})


@dataclass(frozen=True)
class SchemaStatement:
    """Generated schema SQL statement."""

    query: str


@dataclass(frozen=True)
class SchemaMetadata:
    """Relevant Exasol schema metadata for lifecycle decisions."""

    name: str
    owner: str | None = None


# -----------------------------
# Public API
# -----------------------------


def ensure_schema(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure an Exasol schema is present or absent, with the requested owner."""
    schema_name = exact_schema_name(validate_required_param(params, "name"))
    state = schema_state(params)
    metadata = schema_metadata(connection, schema_name)

    statements = planned_schema_statements(
        schema_name=schema_name,
        metadata=metadata,
        params=params,
    )

    if statements and not check_mode:
        common_query.execute_queries(
            connection,
            [s.query for s in statements],
        )

    owner = _requested_owner(params)
    return {
        "changed": bool(statements),
        "schema": schema_name,
        "state": state,
        "exists": state == "present" if statements else metadata is not None,
        "owner": owner if owner is not None else (metadata.owner if metadata else None),
        "executed_queries": [s.query for s in statements],
    }


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for schema lifecycle parameters."""
    return {
        **common_query.exasol_connection_argument_spec(),
        "name": {"type": "str", "required": True, "aliases": ["schema"]},
        "owner": {"type": "str"},
        "state": {
            "type": "str",
            "choices": sorted(STATES),
            "default": DEFAULT_STATE,
        },
        "cascade": {"type": "bool", "default": DEFAULT_CASCADE},
    }


def run_schema(
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Connect to Exasol and manage the requested schema."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_schema",
    ) as connection:
        return ensure_schema(
            connection,
            params,
            check_mode=check_mode,
        )


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact sensitive data from an error message."""
    return common_query.sanitize_error_message(error, params)


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol schema management",
) -> str:
    """Return a sanitized user-facing error message."""
    return common_query.normalized_exasol_error_message(
        error,
        params=params,
        operation=operation,
    )


# -----------------------------
# Internal logic (also reused directly by exasol_init phase planning)
# -----------------------------


def exact_schema_name(name: str) -> str:
    """Validate and return the exact Exasol schema identifier value."""
    return validate_schema_name(name)


def schema_metadata(connection: object, name: str) -> SchemaMetadata | None:
    """Probe EXA_ALL_SCHEMAS for the current owner of a schema, if it exists."""
    result = common_query.execute_queries(
        connection,
        SCHEMA_METADATA_QUERY,
        named_args={"schema_name": name},
    )
    rows = result["query_result"]
    if not rows:
        return None

    row = rows[0]
    if not isinstance(row, Mapping):
        raise ValueError("unexpected row shape for Exasol schema metadata.")

    return SchemaMetadata(
        name=str(row["SCHEMA_NAME"]),
        owner=_optional_string(row.get("SCHEMA_OWNER")),
    )


def planned_schema_statements(
    schema_name: str,
    metadata: SchemaMetadata | None,
    params: Mapping[str, object],
) -> list[SchemaStatement]:
    """Plan the minimal SQL statements needed to reconcile one schema."""
    state = schema_state(params)

    if state == "absent":
        if metadata is None:
            return []

        return [
            SchemaStatement(_drop_schema_query(schema_name, schema_cascade(params)))
        ]

    owner = _requested_owner(params)

    if metadata is None:
        statements = [SchemaStatement(f"CREATE SCHEMA {quote_identifier(schema_name)}")]
        if owner is not None:
            statements.append(_change_owner_statement(schema_name, owner))
        return statements

    if owner is not None and _normalized(owner) != _normalized(metadata.owner):
        return [_change_owner_statement(schema_name, owner)]

    return []


def _change_owner_statement(schema_name: str, owner: str) -> SchemaStatement:
    quoted_schema = quote_identifier(schema_name)
    quoted_owner = quote_exact_identifier_value(
        validate_user_name(owner), identifier_type="user"
    )
    return SchemaStatement(f"ALTER SCHEMA {quoted_schema} CHANGE OWNER {quoted_owner}")


def _drop_schema_query(schema_name: str, cascade: bool) -> str:
    query = f"DROP SCHEMA {quote_identifier(schema_name)}"
    return f"{query} CASCADE" if cascade else query


def schema_cascade(params: Mapping[str, object]) -> bool:
    """Return the requested cascade flag for a schema drop."""
    return bool(params.get("cascade", DEFAULT_CASCADE))


def schema_state(params: Mapping[str, object]) -> str:
    """Validate and return the requested schema lifecycle state."""
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)


def _requested_owner(params: Mapping[str, object]) -> str | None:
    owner = params.get("owner")
    return owner if isinstance(owner, str) and owner else None


def _normalized(value: str | None) -> str | None:
    return value.casefold() if value is not None else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
