"""Ansible-facing exasol_user runtime; delegates to common_user."""

from __future__ import annotations

from collections.abc import Mapping

from exasol.ansible_modules import (
    common_query,
    common_user,
)
from exasol.ansible_modules.common_user import (  # noqa: F401 (re-exported for tests)
    _quote_password_identifier,
    _quote_sql_string_literal,
    _user_metadata,
)

module_argument_spec = common_user.module_argument_spec
sanitize_error_message = common_user.sanitize_error_message
normalized_exasol_error_message = common_user.normalized_exasol_error_message


def ensure_user(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure an Exasol user is present or absent."""
    return common_user.ensure_user(connection, params, check_mode=check_mode)


def run_user(
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Connect to Exasol and manage the requested user."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_user",
    ) as connection:
        return ensure_user(
            connection,
            params,
            check_mode=check_mode,
        )
