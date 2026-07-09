"""Reusable Exasol role lifecycle logic."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier,
    validate_role_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

DEFAULT_STATE = "present"
DEFAULT_CASCADE = False

ROLE_EXISTS_QUERY = """
                    SELECT ROLE_NAME
                    FROM EXA_ALL_ROLES
                    WHERE UPPER(ROLE_NAME) = UPPER(:role_name) \
                    """

STATES = frozenset({"present", "absent"})


@dataclass(frozen=True)
class RoleStatement:
    """Generated role SQL statement."""

    query: str


# -----------------------------
# Public API
# -----------------------------


def ensure_role(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure an Exasol role is present or absent."""

    role_name = _exact_role_name(validate_required_param(params, "name"))

    state = _state(params)
    exists_before = _role_exists(connection, role_name)

    statements = _planned_role_statements(
        role_name=role_name,
        exists=exists_before,
        params=params,
    )

    if statements and not check_mode:
        common_query.execute_queries(
            connection,
            [s.query for s in statements],
        )

    return {
        "changed": bool(statements),
        "role": role_name,
        "state": state,
        "exists": state == "present" if statements else exists_before,
        "executed_queries": [s.query for s in statements],
    }


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact sensitive data from error message."""
    return common_query.sanitize_error_message(error, params)


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol role management",
) -> str:
    """Return sanitized user-facing error message."""
    return common_query.normalized_exasol_error_message(
        error,
        params=params,
        operation=operation,
    )


# -----------------------------
# Internal logic
# -----------------------------


def _exact_role_name(name: str) -> str:
    return validate_role_name(name)


def _role_exists(connection: object, name: str) -> bool:
    result = common_query.execute_queries(
        connection,
        ROLE_EXISTS_QUERY,
        named_args={"role_name": name},
    )
    return bool(result["query_result"])


def _planned_role_statements(
    role_name: str,
    exists: bool,
    params: Mapping[str, object],
) -> list[RoleStatement]:

    state = _state(params)

    if state == "absent":
        if not exists:
            return []

        return [RoleStatement(_drop_role_query(role_name, _cascade(params)))]

    if exists:
        return []

    return [
        RoleStatement(
            f"CREATE ROLE {quote_exact_identifier(role_name, identifier_type='role')}"
        )
    ]


def _drop_role_query(role_name: str, cascade: bool) -> str:
    query = f"DROP ROLE {quote_exact_identifier(role_name, identifier_type='role')}"
    return f"{query} CASCADE" if cascade else query


def _cascade(params: Mapping[str, object]) -> bool:
    return bool(params.get("cascade", DEFAULT_CASCADE))


def _state(params: Mapping[str, object]) -> str:
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)
