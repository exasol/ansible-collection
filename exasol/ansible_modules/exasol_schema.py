"""Reusable Exasol schema lifecycle logic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    validate_schema_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

DEFAULT_STATE = "present"
DEFAULT_CASCADE = False

STATES = frozenset({"present", "absent"})


SCHEMA_METADATA_QUERY = """
                        SELECT SCHEMA_NAME
                        FROM EXA_SCHEMAS
                        WHERE UPPER(SCHEMA_NAME) = UPPER(:schema_name)
                        """


@dataclass(frozen=True)
class SchemaStatement:
    """Generated SQL statement with its public representation."""

    actual: str
    public: str


@dataclass(frozen=True)
class SchemaMetadata:
    """Relevant Exasol schema metadata."""

    name: str


def ensure_schema(
    connection: object, params: Mapping[str, object], check_mode: bool = False
) -> dict[str, object]:
    """Ensure an Exasol schema is present or absent."""
    schema_name = _exact_schema_name(validate_required_param(params, "name"))

    state = _state(params)

    metadata = _schema_metadata(connection, schema_name)

    statements = _planned_schema_statements(
        schema_name=schema_name, metadata=metadata, params=params
    )

    if statements:
        if not check_mode:
            common_query.execute_queries(
                connection, [statement.actual for statement in statements]
            )

        exists = state == "present"
    else:
        exists = metadata is not None

    return {
        "changed": bool(statements),
        "schema": schema_name,
        "state": state,
        "exists": exists,
        "executed_queries": [statement.public for statement in statements],
    }


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Sanitize schema-related errors."""
    return common_query.sanitize_error_message(error, params)


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol schema management",
) -> str:
    """Return normalized Exasol schema error."""
    return common_query.normalized_exasol_error_message(
        error, params=params, operation=operation
    )


def _exact_schema_name(name: str) -> str:
    return validate_schema_name(name)


def _schema_metadata(connection: object, schema_name: str) -> SchemaMetadata | None:
    result = common_query.execute_queries(
        connection, [SCHEMA_METADATA_QUERY], named_args={"schema_name": schema_name}
    )

    rows = result["query_result"]

    if not rows:
        return None

    row = rows[0]

    if not isinstance(row, dict):
        raise ValueError(
            f"unexpected row shape for Exasol schema metadata: {type(row).__name__}"
        )

    schema_name_value = row.get("SCHEMA_NAME")

    if schema_name_value is None:
        raise ValueError("missing SCHEMA_NAME in Exasol schema metadata.")

    return SchemaMetadata(name=str(schema_name_value))


def _planned_schema_statements(
    schema_name: str, metadata: SchemaMetadata | None, params: Mapping[str, object]
) -> list[SchemaStatement]:
    state = _state(params)

    if state == "absent":
        return _planned_drop_schema_statements(schema_name, metadata, params)

    if metadata is not None:
        return []

    return [_create_schema_statement(schema_name)]


def _planned_drop_schema_statements(
    schema_name: str, metadata: SchemaMetadata | None, params: Mapping[str, object]
) -> list[SchemaStatement]:
    if metadata is None:
        return []

    return [
        _drop_schema_statement(
            schema_name, cascade=bool(params.get("cascade", DEFAULT_CASCADE))
        )
    ]


def _create_schema_statement(schema_name: str) -> SchemaStatement:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")

    query = f"CREATE SCHEMA {quoted_schema}"

    return SchemaStatement(actual=query, public=query)


def _drop_schema_statement(schema_name: str, cascade: bool) -> SchemaStatement:
    quoted_schema = quote_exact_identifier_value(schema_name, identifier_type="schema")

    query = f"DROP SCHEMA {quoted_schema}"

    if cascade:
        query += " CASCADE"

    return SchemaStatement(actual=query, public=query)


def _state(params: Mapping[str, object]) -> str:
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)
