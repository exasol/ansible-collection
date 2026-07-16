"""Shared user assertions for integration tests."""

from __future__ import annotations

from ansible_playbook.common_helpers import connect_to_exasol


def assert_user_can_log_in(
    exasol_login_vars: dict[str, object], user_name: str, password: str
) -> None:
    """Assert that an Exasol user can log in with the supplied password."""
    connection = connect_to_exasol(
        {
            **exasol_login_vars,
            "login_user": user_name,
            "login_password": password,
        }
    )
    try:
        login_rows = connection.execute("SELECT 1 AS LOGIN_OK").fetchall()
    finally:
        connection.close()

    assert login_rows == [{"LOGIN_OK": 1}]
