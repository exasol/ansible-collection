"""exasol_role-specific pyexasol mock scenarios."""

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


def connect(**kwargs: Any) -> RoleMockConnection:
    """Return an exasol_role-specific mock Exasol connection."""
    password = kwargs.get("password")
    if isinstance(password, str) and password in AUTHENTICATION_ERRORS:
        raise RuntimeError(AUTHENTICATION_ERRORS[password])

    return RoleMockConnection(connect_kwargs=kwargs)


class RoleMockConnection:
    """Stateful mock connection for role-management scenarios."""

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

        if upper_query.startswith("SELECT ROLE_NAME FROM EXA_ALL_ROLES"):
            return role_exists_statement(params)

        if upper_query.startswith("CREATE ROLE"):
            return create_role_statement(upper_query)

        if upper_query.startswith("DROP ROLE"):
            return drop_role_statement(upper_query)

        raise RuntimeError(f"unexpected mock query: {query}")

    def close(self) -> None:
        """Close the mock connection."""
        self.closed = True


def role_exists_statement(params: dict[str, Any]) -> MockStatement:
    state = load_state()
    role_name = str(params["role_name"]).upper()
    rows = [{"ROLE_NAME": role_name}] if role_name in state["roles"] else []

    return result_statement(rows=rows, rowcount=len(rows))


def create_role_statement(query: str) -> MockStatement:
    state = load_state()
    state["roles"].add(quoted_identifier(query))
    save_state(state)

    return rowcount_statement()


def drop_role_statement(query: str) -> MockStatement:
    state = load_state()
    state["roles"].discard(quoted_identifier(query))
    save_state(state)

    return rowcount_statement()


def quoted_identifier(query: str) -> str:
    """Return the first quoted identifier from a generated role statement."""
    return query.split('"', 2)[1]


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"roles": set()}

    raw_state = json.loads(path.read_text(encoding="utf-8"))
    return {"roles": set(raw_state.get("roles", []))}


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = {"roles": sorted(state["roles"])}
    path.write_text(json.dumps(serialized), encoding="utf-8")


def state_path() -> Path:
    path = os.environ.get("EXASOL_ROLE_MOCK_STATE")
    if not path:
        raise RuntimeError("EXASOL_ROLE_MOCK_STATE is not configured")

    return Path(path)
