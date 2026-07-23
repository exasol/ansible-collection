"""Shared helpers for Ansible module runtime integration tests."""

from __future__ import annotations

import uuid

from exasol.ansible_modules import exasol_query


def unique_name(prefix: str) -> str:
    """Return a unique Exasol object name for one integration test."""
    return f"{prefix}_{uuid.uuid4().hex.upper()}"


def execute_sql(login_vars: dict[str, object], query: str) -> None:
    """Execute one SQL statement through a plain Exasol connection."""
    with exasol_query.connect_to_exasol(
        login_vars,
        module_name="python package integration test",
    ) as connection:
        connection.execute(query)
