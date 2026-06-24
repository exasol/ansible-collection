"""exasol_user-specific pyexasol mock scenarios."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pyexasol_mock_base import (
    MockStatement,
    normalize_query,
    result_statement,
    rowcount_statement,
)

AUTHENTICATION_ERRORS = {
    "bad-secret": "authentication failed for password bad-secret",
}


def connect(**kwargs: Any) -> UserMockConnection:
    """Return an exasol_user-specific mock Exasol connection."""
    password = kwargs.get("password")
    if isinstance(password, str) and password in AUTHENTICATION_ERRORS:
        raise RuntimeError(AUTHENTICATION_ERRORS[password])

    return UserMockConnection(connect_kwargs=kwargs)


class UserMockConnection:
    """Stateful mock connection for user-management scenarios."""

    def __init__(self, connect_kwargs: dict[str, Any]) -> None:
        self.connect_kwargs = connect_kwargs
        self.closed = False

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> MockStatement:
        """Execute a mock SQL statement."""
        normalized_query = normalize_query(query)
        upper_query = normalized_query.upper()
        params = query_params or {}

        if upper_query.startswith("SELECT USER_NAME, DISTINGUISHED_NAME"):
            return user_metadata_statement(params)

        if upper_query.startswith("CREATE USER"):
            return create_user_statement(upper_query)

        if upper_query.startswith("GRANT CREATE SESSION TO"):
            return grant_create_session_statement(upper_query)

        if upper_query.startswith("ALTER USER"):
            return alter_user_statement(upper_query)

        if upper_query.startswith("DROP USER"):
            return drop_user_statement(upper_query)

        raise RuntimeError(f"unexpected mock query: {query}")

    def close(self) -> None:
        """Close the mock connection."""
        self.closed = True


def user_metadata_statement(params: dict[str, Any]) -> MockStatement:
    state = load_state()
    user_name = str(params["user_name"]).upper()
    rows = (
        [
            {
                "USER_NAME": user_name,
                "DISTINGUISHED_NAME": state["users"][user_name].get("ldap_dn"),
            }
        ]
        if user_name in state["users"]
        else []
    )

    return result_statement(rows=rows, rowcount=len(rows))


def create_user_statement(query: str) -> MockStatement:
    state = load_state()
    user_name = quoted_identifier(query)
    state["users"][user_name] = {
        "create_session": False,
        "password_updates": 0,
        "ldap_dn": ldap_dn_from_query(query),
    }
    save_state(state)

    return rowcount_statement()


def grant_create_session_statement(query: str) -> MockStatement:
    state = load_state()
    user_name = quoted_identifier(query)
    state["users"].setdefault(
        user_name,
        {"create_session": False, "password_updates": 0, "ldap_dn": None},
    )
    state["users"][user_name]["create_session"] = True
    save_state(state)

    return rowcount_statement()


def alter_user_statement(query: str) -> MockStatement:
    state = load_state()
    user_name = quoted_identifier(query)
    state["users"].setdefault(
        user_name,
        {"create_session": False, "password_updates": 0, "ldap_dn": None},
    )
    if " IDENTIFIED AT LDAP AS " in query:
        state["users"][user_name]["ldap_dn"] = ldap_dn_from_query(query)
    else:
        state["users"][user_name]["password_updates"] += 1
    save_state(state)

    return rowcount_statement()


def drop_user_statement(query: str) -> MockStatement:
    state = load_state()
    state["users"].pop(quoted_identifier(query), None)
    save_state(state)

    return rowcount_statement()


def quoted_identifier(query: str) -> str:
    """Return the first quoted identifier from a generated user statement."""
    return query.split('"', 2)[1]


def ldap_dn_from_query(query: str) -> str | None:
    """Return LDAP DN from generated LDAP user syntax, if present."""
    marker = " IDENTIFIED AT LDAP AS "
    if marker not in query:
        return None

    return query.split(marker, 1)[1].strip("'")


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"users": {}}

    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def state_path() -> Path:
    path = os.environ.get("EXASOL_USER_MOCK_STATE")
    if not path:
        raise RuntimeError("EXASOL_USER_MOCK_STATE is not configured")

    return Path(path)
