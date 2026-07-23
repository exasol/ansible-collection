"""exasol_grants-specific pyexasol mock scenarios."""

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


def connect(**kwargs: Any) -> GrantsMockConnection:
    """Return an exasol_grants-specific mock Exasol connection."""
    password = kwargs.get("password")
    if isinstance(password, str) and password in AUTHENTICATION_ERRORS:
        raise RuntimeError(AUTHENTICATION_ERRORS[password])

    return GrantsMockConnection(connect_kwargs=kwargs)


class GrantsMockConnection:
    """Stateful mock connection for grant-management scenarios."""

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
        params = query_params or {}

        if normalized_query.startswith(
            "SELECT PRIVILEGE, ADMIN_OPTION FROM EXA_DBA_SYS_PRIVS"
        ):
            return system_privilege_statement(params)

        if normalized_query.startswith("SELECT PRIVILEGE FROM EXA_DBA_OBJ_PRIVS"):
            return object_privilege_statement(params)

        if normalized_query.startswith(
            "SELECT GRANTED_ROLE, ADMIN_OPTION FROM EXA_DBA_ROLE_PRIVS"
        ):
            return role_grant_statement(params)

        if normalized_query.startswith("GRANT "):
            grant_statement(normalized_query)
            return rowcount_statement()

        if normalized_query.startswith("REVOKE "):
            revoke_statement(normalized_query)
            return rowcount_statement()

        raise RuntimeError(f"unexpected mock query: {query}")

    def close(self) -> None:
        """Close the mock connection."""
        self.closed = True


def system_privilege_statement(params: dict[str, Any]) -> MockStatement:
    state = load_state()
    key = system_key(str(params["principal"]), str(params["privilege"]))
    rows = [
        {"PRIVILEGE": privilege, "ADMIN_OPTION": admin_option}
        for principal, privilege, admin_option in state["system_grants"]
        if (principal, privilege) == key
    ]

    return result_statement(rows=rows, rowcount=len(rows))


def object_privilege_statement(params: dict[str, Any]) -> MockStatement:
    state = load_state()
    object_name = params["object_name"]
    key = object_key(
        str(params["principal"]),
        str(params["privilege"]),
        str(params["schema_name"]),
        str(object_name) if object_name is not None else None,
    )
    rows = [{"PRIVILEGE": key[1]}] if key in state["object_grants"] else []

    return result_statement(rows=rows, rowcount=len(rows))


def role_grant_statement(params: dict[str, Any]) -> MockStatement:
    state = load_state()
    key = role_key(str(params["principal"]), str(params["granted_role"]))
    rows = [
        {"GRANTED_ROLE": granted_role, "ADMIN_OPTION": admin_option}
        for principal, granted_role, admin_option in state["role_grants"]
        if (principal, granted_role) == key
    ]

    return result_statement(rows=rows, rowcount=len(rows))


def grant_statement(query: str) -> None:
    state = load_state()

    if " ON " not in query:
        grant_name, principal, admin_option = grant_statement_parts(
            query,
            "GRANT ",
            " TO ",
        )
        if is_role_grant_statement(query):
            state["role_grants"].discard((*role_key(principal, grant_name), False))
            state["role_grants"].discard((*role_key(principal, grant_name), True))
            state["role_grants"].add((*role_key(principal, grant_name), admin_option))
        else:
            state["system_grants"].discard((*system_key(principal, grant_name), False))
            state["system_grants"].discard((*system_key(principal, grant_name), True))
            state["system_grants"].add(
                (*system_key(principal, grant_name), admin_option)
            )
    else:
        privilege, schema_name, object_name, principal = object_statement_parts(
            query,
            "GRANT ",
            " TO ",
        )
        state["object_grants"].add(
            object_key(principal, privilege, schema_name, object_name)
        )

    save_state(state)


def revoke_statement(query: str) -> None:
    state = load_state()

    if " ON " not in query:
        grant_name, principal, _admin_option = grant_statement_parts(
            query,
            "REVOKE ",
            " FROM ",
        )
        if is_role_grant_statement(query):
            state["role_grants"].discard((*role_key(principal, grant_name), False))
            state["role_grants"].discard((*role_key(principal, grant_name), True))
        else:
            state["system_grants"].discard((*system_key(principal, grant_name), False))
            state["system_grants"].discard((*system_key(principal, grant_name), True))
    else:
        privilege, schema_name, object_name, principal = object_statement_parts(
            query,
            "REVOKE ",
            " FROM ",
        )
        state["object_grants"].discard(
            object_key(principal, privilege, schema_name, object_name)
        )

    save_state(state)


def grant_statement_parts(
    query: str,
    prefix: str,
    principal_separator: str,
) -> tuple[str, str, bool]:
    body = query.removeprefix(prefix)
    admin_option = body.endswith(" WITH ADMIN OPTION")
    if admin_option:
        body = body.removesuffix(" WITH ADMIN OPTION")

    grant_name, principal_part = body.split(principal_separator, 1)
    if grant_name.startswith('"'):
        grant_name = quoted_identifiers(grant_name)[0]

    return grant_name, quoted_identifiers(principal_part)[0], admin_option


def is_role_grant_statement(query: str) -> bool:
    return query.removeprefix("GRANT ").removeprefix("REVOKE ").startswith('"')


def object_statement_parts(
    query: str,
    prefix: str,
    principal_separator: str,
) -> tuple[str, str, str | None, str]:
    body = query.removeprefix(prefix)
    privilege, rest = body.split(" ON ", 1)
    target_part, principal_part = rest.split(principal_separator, 1)
    target_identifiers = quoted_identifiers(target_part)
    principal = quoted_identifiers(principal_part)[0]

    if len(target_identifiers) == 1:
        return privilege, target_identifiers[0], None, principal

    return privilege, target_identifiers[0], target_identifiers[1], principal


def quoted_identifiers(query: str) -> list[str]:
    """Return quoted identifiers from a generated grant statement."""
    identifiers: list[str] = []
    index = 0

    while index < len(query):
        if query[index] != '"':
            index += 1
            continue

        value: list[str] = []
        index += 1
        while index < len(query):
            char = query[index]
            if char != '"':
                value.append(char)
                index += 1
                continue

            if index + 1 < len(query) and query[index + 1] == '"':
                value.append('"')
                index += 2
                continue

            identifiers.append("".join(value))
            index += 1
            break

    return identifiers


def system_key(principal: str, privilege: str) -> tuple[str, str]:
    return principal.casefold(), privilege.upper()


def role_key(principal: str, role_name: str) -> tuple[str, str]:
    return principal.casefold(), role_name.casefold()


def object_key(
    principal: str,
    privilege: str,
    schema_name: str,
    object_name: str | None,
) -> tuple[str, str, str, str | None]:
    return (
        principal.casefold(),
        privilege.upper(),
        schema_name.casefold(),
        object_name.casefold() if object_name is not None else None,
    )


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {"system_grants": set(), "role_grants": set(), "object_grants": set()}

    raw_state = json.loads(path.read_text(encoding="utf-8"))
    return {
        "system_grants": {tuple(item) for item in raw_state.get("system_grants", [])},
        "role_grants": {tuple(item) for item in raw_state.get("role_grants", [])},
        "object_grants": {tuple(item) for item in raw_state.get("object_grants", [])},
    }


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = {
        "system_grants": sorted(list(state["system_grants"])),
        "role_grants": sorted(list(state["role_grants"])),
        "object_grants": sorted(list(state["object_grants"])),
    }
    path.write_text(json.dumps(serialized), encoding="utf-8")


def state_path() -> Path:
    path = os.environ.get("EXASOL_GRANTS_MOCK_STATE")
    if not path:
        raise RuntimeError("EXASOL_GRANTS_MOCK_STATE is not configured")

    return Path(path)
