"""Reusable Exasol schema lifecycle logic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    validate_exact_identifier,
    validate_schema_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

DEFAULT_STATE = "present"
DEFAULT_CASCADE = False
MAX_SCHEMA_COMMENT_LENGTH = 2000

STATES = frozenset({"present", "absent"})


SCHEMA_METADATA_QUERY = """
                        SELECT S.SCHEMA_NAME,
                               S.SCHEMA_OWNER,
                               S.SCHEMA_COMMENT,
                               O.RAW_OBJECT_SIZE_LIMIT AS RAW_SIZE_LIMIT
                        FROM EXA_SCHEMAS S
                        LEFT JOIN EXA_ALL_OBJECT_SIZES O
                          ON O.OBJECT_ID = S.SCHEMA_OBJECT_ID
                         AND O.OBJECT_TYPE = 'SCHEMA'
                        WHERE UPPER(S.SCHEMA_NAME) = UPPER(:schema_name)
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
    owner: str | None
    comment: str | None
    raw_size_limit: int | None


def ensure_schema(
    connection: object, params: Mapping[str, object], check_mode: bool = False
) -> dict[str, object]:
    """Ensure an Exasol schema has the requested lifecycle state."""
    schema_name = _exact_schema_name(validate_required_param(params, "name"))
    state = _state(params)
    new_name = _optional_schema_name(params, "new_name")
    _validate_state_options(params, state, new_name)

    metadata = _schema_metadata(connection, schema_name)
    target_metadata = None
    if new_name is not None and not _same_identifier(schema_name, new_name):
        target_metadata = _schema_metadata(connection, new_name)

    effective_name, effective_metadata, statements = _planned_schema_statements(
        schema_name=schema_name,
        new_name=new_name,
        metadata=metadata,
        target_metadata=target_metadata,
        params=params,
    )

    if statements and not check_mode:
        common_query.execute_queries(
            connection, [statement.actual for statement in statements]
        )

    if statements:
        exists = state == "present"
    else:
        exists = effective_metadata is not None

    return {
        "changed": bool(statements),
        "schema": effective_name,
        "state": state,
        "exists": exists,
        "executed_queries": [statement.public for statement in statements],
    }


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the schema module."""
    return {
        **common_query.exasol_connection_argument_spec(),
        "name": {"type": "str", "required": True, "aliases": ["schema"]},
        "state": {
            "type": "str",
            "choices": sorted(STATES),
            "default": DEFAULT_STATE,
        },
        "cascade": {"type": "bool", "default": DEFAULT_CASCADE},
        "owner": {"type": "str"},
        "comment": {"type": "str"},
        "new_name": {"type": "str"},
        "raw_size_limit": {"type": "int"},
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
        return ensure_schema(connection, params, check_mode=check_mode)


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


def _optional_schema_name(params: Mapping[str, object], name: str) -> str | None:
    value = params.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string.")
    return validate_schema_name(value)


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

    raw_size_limit = row.get("RAW_SIZE_LIMIT")
    return SchemaMetadata(
        name=str(schema_name_value),
        owner=_optional_string_metadata(row.get("SCHEMA_OWNER")),
        comment=_optional_string_metadata(row.get("SCHEMA_COMMENT")),
        raw_size_limit=_optional_integer_metadata(raw_size_limit),
    )


def _optional_string_metadata(value: object) -> str | None:
    return None if value is None else str(value)


def _optional_integer_metadata(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("unexpected RAW_SIZE_LIMIT value in Exasol schema metadata.")
    return int(value)


def _planned_schema_statements(
    schema_name: str,
    new_name: str | None,
    metadata: SchemaMetadata | None,
    target_metadata: SchemaMetadata | None,
    params: Mapping[str, object],
) -> tuple[str, SchemaMetadata | None, list[SchemaStatement]]:
    state = _state(params)
    if state == "absent":
        return (
            schema_name,
            metadata,
            _planned_drop_schema_statements(schema_name, metadata, params),
        )

    effective_name = new_name or schema_name
    effective_metadata = metadata
    statements: list[SchemaStatement] = []

    if new_name is not None and not _same_identifier(schema_name, new_name):
        if metadata is not None and target_metadata is not None:
            raise ValueError(
                "name and new_name both identify existing schemas; refusing to rename."
            )
        if metadata is not None:
            statements.append(_rename_schema_statement(schema_name, new_name))
        effective_metadata = target_metadata or metadata

    if effective_metadata is None:
        statements.append(_create_schema_statement(effective_name))

    statements.extend(
        _planned_schema_property_statements(effective_name, effective_metadata, params)
    )
    return effective_name, effective_metadata, statements


def _planned_schema_property_statements(
    schema_name: str,
    metadata: SchemaMetadata | None,
    params: Mapping[str, object],
) -> list[SchemaStatement]:
    statements: list[SchemaStatement] = []
    comment = _optional_comment(params)
    raw_size_limit = _optional_raw_size_limit(params)
    owner = _optional_owner(params)

    if comment is not None and not _same_comment(metadata, comment):
        statements.append(_comment_schema_statement(schema_name, comment))
    if raw_size_limit is not None and not _same_raw_size_limit(
        metadata, raw_size_limit
    ):
        statements.append(_raw_size_limit_statement(schema_name, raw_size_limit))
    if owner is not None and not _same_owner(metadata, owner):
        statements.append(_change_owner_statement(schema_name, owner))

    return statements


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
    query = f"CREATE SCHEMA {_quoted_schema(schema_name)}"
    return SchemaStatement(actual=query, public=query)


def _rename_schema_statement(schema_name: str, new_name: str) -> SchemaStatement:
    query = f"RENAME SCHEMA {_quoted_schema(schema_name)} TO {_quoted_schema(new_name)}"
    return SchemaStatement(actual=query, public=query)


def _change_owner_statement(schema_name: str, owner: str) -> SchemaStatement:
    quoted_owner = quote_exact_identifier_value(owner, identifier_type="schema owner")
    query = f"ALTER SCHEMA {_quoted_schema(schema_name)} CHANGE OWNER {quoted_owner}"
    return SchemaStatement(actual=query, public=query)


def _comment_schema_statement(schema_name: str, comment: str) -> SchemaStatement:
    value = "NULL" if comment == "" else common_query.quote_sql_string_literal(comment)
    query = f"COMMENT ON SCHEMA {_quoted_schema(schema_name)} IS {value}"
    return SchemaStatement(actual=query, public=query)


def _raw_size_limit_statement(schema_name: str, raw_size_limit: int) -> SchemaStatement:
    query = (
        f"ALTER SCHEMA {_quoted_schema(schema_name)} "
        f"SET RAW_SIZE_LIMIT = {raw_size_limit}"
    )
    return SchemaStatement(actual=query, public=query)


def _drop_schema_statement(schema_name: str, cascade: bool) -> SchemaStatement:
    query = f"DROP SCHEMA {_quoted_schema(schema_name)}"
    if cascade:
        query += " CASCADE"
    return SchemaStatement(actual=query, public=query)


def _quoted_schema(schema_name: str) -> str:
    return quote_exact_identifier_value(schema_name, identifier_type="schema")


def _optional_owner(params: Mapping[str, object]) -> str | None:
    value = params.get("owner")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("owner must be a string.")
    return validate_exact_identifier(value, identifier_type="schema owner")


def _optional_comment(params: Mapping[str, object]) -> str | None:
    value = params.get("comment")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("comment must be a string.")
    if len(value) > MAX_SCHEMA_COMMENT_LENGTH:
        raise ValueError(
            f"comment must not exceed {MAX_SCHEMA_COMMENT_LENGTH} characters."
        )
    common_query.quote_sql_string_literal(value)
    return value


def _optional_raw_size_limit(params: Mapping[str, object]) -> int | None:
    value = params.get("raw_size_limit")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("raw_size_limit must be a non-negative integer.")
    if value < 0:
        raise ValueError("raw_size_limit must be a non-negative integer.")
    return value


def _same_identifier(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def _same_owner(metadata: SchemaMetadata | None, owner: str) -> bool:
    return (
        metadata is not None
        and metadata.owner is not None
        and _same_identifier(metadata.owner, owner)
    )


def _same_comment(metadata: SchemaMetadata | None, comment: str) -> bool:
    current = metadata.comment if metadata is not None else None
    return (current or "") == comment


def _same_raw_size_limit(metadata: SchemaMetadata | None, raw_size_limit: int) -> bool:
    return metadata is not None and metadata.raw_size_limit == raw_size_limit


def _validate_state_options(
    params: Mapping[str, object], state: str, new_name: str | None
) -> None:
    if state == "present":
        return
    incompatible = [
        name
        for name in ("owner", "comment", "raw_size_limit")
        if params.get(name) is not None
    ]
    if new_name is not None:
        incompatible.append("new_name")
    if incompatible:
        raise ValueError(
            f"{', '.join(incompatible)} can only be used with state=present."
        )


def _state(params: Mapping[str, object]) -> str:
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)
