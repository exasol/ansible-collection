"""Reusable Exasol role lifecycle logic, shared by exasol_role and exasol_init."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
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

    role_name = exact_role_name(validate_required_param(params, "name"))

    state = role_state(params)
    exists_before = role_exists(connection, role_name)

    statements = planned_role_statements(
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


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the role module."""
    return {
        **common_query.exasol_connection_argument_spec(),
        "name": {"type": "str", "required": True, "aliases": ["role"]},
        "state": {
            "type": "str",
            "choices": sorted(STATES),
            "default": DEFAULT_STATE,
        },
        "cascade": {"type": "bool", "default": DEFAULT_CASCADE},
    }


def run_role(
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Connect to Exasol and manage the requested role."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_role",
    ) as connection:
        return ensure_role(
            connection,
            params,
            check_mode=check_mode,
        )


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
# Internal logic (also reused directly by exasol_init phase planning)
# -----------------------------


def exact_role_name(name: str) -> str:
    """Validate and return the exact Exasol role identifier value."""
    return validate_role_name(name)


def role_exists(connection: object, name: str) -> bool:
    """Return whether a role with the given exact name currently exists."""
    result = common_query.execute_queries(
        connection,
        ROLE_EXISTS_QUERY,
        named_args={"role_name": name},
    )
    return bool(result["query_result"])


def planned_role_statements(
    role_name: str,
    exists: bool,
    params: Mapping[str, object],
) -> list[RoleStatement]:
    """Plan the minimal SQL statements needed to reconcile one role."""
    state = role_state(params)

    if state == "absent":
        if not exists:
            return []

        return [RoleStatement(drop_role_query(role_name, role_cascade(params)))]

    if exists:
        return []

    return [
        RoleStatement(
            "CREATE ROLE "
            f"{quote_exact_identifier_value(role_name, identifier_type='role')}"
        )
    ]


def drop_role_query(role_name: str, cascade: bool) -> str:
    """Return a DROP ROLE statement, optionally with CASCADE."""
    query = (
        f"DROP ROLE {quote_exact_identifier_value(role_name, identifier_type='role')}"
    )
    return f"{query} CASCADE" if cascade else query


def role_cascade(params: Mapping[str, object]) -> bool:
    """Return the requested cascade flag for a role drop."""
    return bool(params.get("cascade", DEFAULT_CASCADE))


def role_state(params: Mapping[str, object]) -> str:
    """Validate and return the requested role lifecycle state."""
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)
