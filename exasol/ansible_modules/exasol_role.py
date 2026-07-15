"""Ansible-facing exasol_role runtime; delegates to common_role."""

from __future__ import annotations

from collections.abc import Mapping

from exasol.ansible_modules import (
    common_query,
    common_role,
)

module_argument_spec = common_role.module_argument_spec
sanitize_error_message = common_role.sanitize_error_message
normalized_exasol_error_message = common_role.normalized_exasol_error_message


def ensure_role(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure an Exasol role is present or absent."""
    return common_role.ensure_role(connection, params, check_mode=check_mode)


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
