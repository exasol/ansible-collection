"""Tests for exasol_init orchestration runtime behavior."""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from exasol.ansible_modules import exasol_init


class FakeStatement:
    """Small pyexasol statement stand-in for init runtime tests."""

    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        result_type: str = "resultSet",
        rowcount: int = 0,
    ) -> None:
        self._rows = rows or []
        self.result_type = result_type
        self._rowcount = rowcount
        self.execution_time = 0.001

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows

    def rowcount(self) -> int:
        return self._rowcount


class FakeConnection:
    """In-memory Exasol catalog stand-in exercising every exasol_init phase."""

    def __init__(self) -> None:
        self.roles: set[str] = set()
        self.users: set[str] = set()
        self.schemas: dict[str, str | None] = {}
        self.role_grants: set[tuple[str, str]] = set()
        self.schema_grants: set[tuple[str, str, str]] = set()
        self.tables: set[str] = set()
        self.executed: list[str] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized = " ".join(query.split())
        self.executed.append(normalized)
        params = query_params or {}

        if normalized.startswith("SELECT ROLE_NAME FROM EXA_ALL_ROLES"):
            return self._probe_role(params)
        if normalized.startswith("SELECT USER_NAME, DISTINGUISHED_NAME"):
            return self._probe_user(params)
        if normalized.startswith("SELECT SCHEMA_NAME, SCHEMA_OWNER"):
            return self._probe_schema(params)
        if normalized.startswith("SELECT GRANTEE, GRANTED_ROLE"):
            return self._probe_role_grant(params)
        if normalized.startswith("SELECT OBJECT_NAME, GRANTEE, PRIVILEGE"):
            return self._probe_schema_grant(params)
        if normalized.startswith("CREATE ROLE"):
            self.roles.add(_quoted_identifier(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("DROP ROLE"):
            self._discard(self.roles, _quoted_identifier(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("CREATE USER"):
            self.users.add(_quoted_identifier(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("GRANT CREATE SESSION"):
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("DROP USER"):
            self._discard(self.users, _quoted_identifier(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("CREATE SCHEMA"):
            self.schemas[_quoted_identifier(normalized)] = None
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("ALTER SCHEMA"):
            schema, owner = _quoted_identifiers(normalized)[:2]
            self.schemas[schema] = owner
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("DROP SCHEMA"):
            self.schemas.pop(_quoted_identifier(normalized), None)
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("GRANT") and " ON SCHEMA " in normalized:
            self.schema_grants.add(_schema_grant_key(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("REVOKE") and " ON SCHEMA " in normalized:
            self.schema_grants.discard(_schema_grant_key(normalized))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("GRANT") and " TO " in normalized:
            role, user = _quoted_identifiers(normalized)[:2]
            self.role_grants.add((role, user))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("REVOKE") and " FROM " in normalized:
            role, user = _quoted_identifiers(normalized)[:2]
            self.role_grants.discard((role, user))
            return FakeStatement(result_type="rowCount")
        if normalized.startswith("CREATE TABLE"):
            self.tables.add(normalized)
            return FakeStatement(result_type="rowCount")

        raise RuntimeError(f"unexpected query: {query}")

    def _probe_role(self, params: dict[str, Any]) -> FakeStatement:
        match = _case_insensitive_match(self.roles, str(params["role_name"]))
        rows = [{"ROLE_NAME": match}] if match else []
        return FakeStatement(rows=rows, rowcount=len(rows))

    def _probe_user(self, params: dict[str, Any]) -> FakeStatement:
        match = _case_insensitive_match(self.users, str(params["user_name"]))
        rows = [{"USER_NAME": match, "DISTINGUISHED_NAME": None}] if match else []
        return FakeStatement(rows=rows, rowcount=len(rows))

    def _probe_schema(self, params: dict[str, Any]) -> FakeStatement:
        name = str(params["schema_name"])
        for schema_name, owner in self.schemas.items():
            if schema_name.upper() == name.upper():
                return FakeStatement(
                    rows=[{"SCHEMA_NAME": schema_name, "SCHEMA_OWNER": owner}],
                    rowcount=1,
                )
        return FakeStatement(rows=[], rowcount=0)

    def _probe_role_grant(self, params: dict[str, Any]) -> FakeStatement:
        role, grantee = str(params["role"]), str(params["grantee"])
        found = any(
            r.upper() == role.upper() and u.upper() == grantee.upper()
            for r, u in self.role_grants
        )
        return FakeStatement(rows=[{"x": 1}] if found else [], rowcount=int(found))

    def _probe_schema_grant(self, params: dict[str, Any]) -> FakeStatement:
        schema = str(params["schema_name"])
        grantee = str(params["grantee"])
        privilege = str(params["privilege"])
        found = any(
            s.upper() == schema.upper()
            and g.upper() == grantee.upper()
            and p.upper() == privilege.upper()
            for s, g, p in self.schema_grants
        )
        return FakeStatement(rows=[{"x": 1}] if found else [], rowcount=int(found))

    @staticmethod
    def _discard(collection: set[str], identifier: str) -> None:
        matched = _case_insensitive_match(collection, identifier)
        if matched is not None:
            collection.discard(matched)


def _quoted_identifier(query: str) -> str:
    return _quoted_identifiers(query)[0]


def _quoted_identifiers(query: str) -> list[str]:
    return re.findall(r'"((?:[^"]|"")*)"', query)


def _schema_grant_key(query: str) -> tuple[str, str, str]:
    match = re.match(
        r"(?:GRANT|REVOKE) (\S+) ON SCHEMA \"([^\"]+)\" (?:TO|FROM) \"([^\"]+)\"",
        query,
    )
    assert match is not None, query
    privilege, schema, grantee = match.groups()
    return schema, grantee, privilege


def _case_insensitive_match(values: set[str], identifier: str) -> str | None:
    for value in values:
        if value.casefold() == identifier.casefold():
            return value
    return None


def test_ensure_init_creates_full_environment_in_dependency_order() -> None:
    """Verify a full run creates every phase in the documented dependency order."""
    connection = FakeConnection()

    result = exasol_init.ensure_init(
        connection,
        {
            "roles": [{"name": "REPORTER"}],
            "users": [{"name": "REPORT_USER", "password": "Initial_Secret_42"}],
            "role_grants": [{"role": "REPORTER", "user": "REPORT_USER"}],
            "schemas": [{"name": "REPORT_SCHEMA", "owner": "REPORT_USER"}],
            "grants": [
                {
                    "schema": "REPORT_SCHEMA",
                    "privilege": "SELECT",
                    "grantee": "REPORTER",
                }
            ],
            "scripts": ["CREATE TABLE REPORT_SCHEMA.EVENTS (ID INT)"],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'CREATE ROLE "REPORTER"',
        'CREATE USER "REPORT_USER" IDENTIFIED BY "********"',
        'GRANT CREATE SESSION TO "REPORT_USER"',
        'GRANT "REPORTER" TO "REPORT_USER"',
        'CREATE SCHEMA "REPORT_SCHEMA"',
        'ALTER SCHEMA "REPORT_SCHEMA" CHANGE OWNER "REPORT_USER"',
        'GRANT SELECT ON SCHEMA "REPORT_SCHEMA" TO "REPORTER"',
        "CREATE TABLE REPORT_SCHEMA.EVENTS (ID INT)",
    ]
    assert "REPORTER" in connection.roles
    assert "REPORT_USER" in connection.users
    assert connection.schemas["REPORT_SCHEMA"] == "REPORT_USER"
    assert ("REPORTER", "REPORT_USER") in connection.role_grants
    assert ("REPORT_SCHEMA", "REPORTER", "SELECT") in connection.schema_grants


def test_ensure_init_reapplying_same_environment_is_idempotent() -> None:
    """Verify re-running an already-initialized environment makes no changes."""
    connection = FakeConnection()
    params = {
        "roles": [{"name": "REPORTER"}],
        "users": [{"name": "REPORT_USER", "password": "Initial_Secret_42"}],
        "role_grants": [{"role": "REPORTER", "user": "REPORT_USER"}],
        "schemas": [{"name": "REPORT_SCHEMA", "owner": "REPORT_USER"}],
        "grants": [
            {"schema": "REPORT_SCHEMA", "privilege": "SELECT", "grantee": "REPORTER"}
        ],
    }
    exasol_init.ensure_init(connection, params)

    result = exasol_init.ensure_init(
        connection,
        {**params, "users": [{**params["users"][0], "update_password": "on_create"}]},
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


def test_ensure_init_scripts_always_execute_after_grants() -> None:
    """Verify scripts run every time, after grants, even on an unchanged environment."""
    connection = FakeConnection()
    params = {
        "roles": [{"name": "CONTENT_READER"}],
        "schemas": [{"name": "CONTENT_SCHEMA"}],
        "grants": [
            {
                "schema": "CONTENT_SCHEMA",
                "privilege": "SELECT",
                "grantee": "CONTENT_READER",
            }
        ],
    }
    exasol_init.ensure_init(connection, params)

    result = exasol_init.ensure_init(
        connection,
        {**params, "scripts": ["CREATE TABLE CONTENT_SCHEMA.ARTICLES (ID INT)"]},
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        "CREATE TABLE CONTENT_SCHEMA.ARTICLES (ID INT)"
    ]


def test_ensure_init_check_mode_predicts_full_plan_without_writing() -> None:
    """Verify check mode plans every phase without mutating the environment."""
    connection = FakeConnection()

    result = exasol_init.ensure_init(
        connection,
        {
            "roles": [{"name": "CHECK_ROLE"}],
            "users": [{"name": "CHECK_USER", "password": "Check_Secret_42"}],
            "role_grants": [{"role": "CHECK_ROLE", "user": "CHECK_USER"}],
            "schemas": [{"name": "CHECK_SCHEMA", "owner": "CHECK_USER"}],
            "grants": [
                {
                    "schema": "CHECK_SCHEMA",
                    "privilege": "SELECT",
                    "grantee": "CHECK_ROLE",
                }
            ],
            "scripts": ["CREATE TABLE CHECK_SCHEMA.T (ID INT)"],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'CREATE ROLE "CHECK_ROLE"',
        'CREATE USER "CHECK_USER" IDENTIFIED BY "********"',
        'GRANT CREATE SESSION TO "CHECK_USER"',
        'GRANT "CHECK_ROLE" TO "CHECK_USER"',
        'CREATE SCHEMA "CHECK_SCHEMA"',
        'ALTER SCHEMA "CHECK_SCHEMA" CHANGE OWNER "CHECK_USER"',
        'GRANT SELECT ON SCHEMA "CHECK_SCHEMA" TO "CHECK_ROLE"',
        "CREATE TABLE CHECK_SCHEMA.T (ID INT)",
    ]
    assert connection.roles == set()
    assert connection.users == set()
    assert connection.schemas == {}
    assert connection.role_grants == set()
    assert connection.schema_grants == set()
    assert "Check_Secret_42" not in json.dumps(result)


def test_ensure_init_optional_phases_are_skipped_when_omitted() -> None:
    """Verify only requested phases produce statements."""
    connection = FakeConnection()

    result = exasol_init.ensure_init(
        connection,
        {
            "roles": [{"name": "MINIMAL_ROLE"}],
            "users": [{"name": "MINIMAL_USER", "password": "Initial_Secret_42"}],
        },
    )

    assert result["executed_queries"] == [
        'CREATE ROLE "MINIMAL_ROLE"',
        'CREATE USER "MINIMAL_USER" IDENTIFIED BY "********"',
        'GRANT CREATE SESSION TO "MINIMAL_USER"',
    ]
    assert result["schemas"] == []
    assert result["grants"] == []
    assert result["scripts"] == {"changed": False, "executed_queries": []}


def test_ensure_init_teardown_reverses_dependency_order() -> None:
    """Verify a full teardown request drops dependents before dependencies."""
    connection = FakeConnection()
    connection.roles.add("TEARDOWN_ROLE")
    connection.users.add("TEARDOWN_USER")
    connection.schemas["TEARDOWN_SCHEMA"] = "TEARDOWN_USER"
    connection.role_grants.add(("TEARDOWN_ROLE", "TEARDOWN_USER"))
    connection.schema_grants.add(("TEARDOWN_SCHEMA", "TEARDOWN_ROLE", "SELECT"))

    result = exasol_init.ensure_init(
        connection,
        {
            "roles": [{"name": "TEARDOWN_ROLE", "state": "absent", "cascade": True}],
            "users": [{"name": "TEARDOWN_USER", "state": "absent", "cascade": True}],
            "role_grants": [
                {"role": "TEARDOWN_ROLE", "user": "TEARDOWN_USER", "state": "absent"}
            ],
            "schemas": [
                {"name": "TEARDOWN_SCHEMA", "state": "absent", "cascade": True}
            ],
            "grants": [
                {
                    "schema": "TEARDOWN_SCHEMA",
                    "privilege": "SELECT",
                    "grantee": "TEARDOWN_ROLE",
                    "state": "absent",
                }
            ],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'REVOKE SELECT ON SCHEMA "TEARDOWN_SCHEMA" FROM "TEARDOWN_ROLE"',
        'REVOKE "TEARDOWN_ROLE" FROM "TEARDOWN_USER"',
        'DROP SCHEMA "TEARDOWN_SCHEMA" CASCADE',
        'DROP USER "TEARDOWN_USER" CASCADE',
        'DROP ROLE "TEARDOWN_ROLE" CASCADE',
    ]
    assert connection.roles == set()
    assert connection.users == set()
    assert connection.schemas == {}


def test_ensure_init_mixed_teardown_and_reconciliation_runs_teardown_first() -> None:
    """Verify absent items are torn down before present items are created."""
    connection = FakeConnection()
    connection.roles.add("OLD_ROLE")

    result = exasol_init.ensure_init(
        connection,
        {
            "roles": [
                {"name": "OLD_ROLE", "state": "absent", "cascade": True},
                {"name": "NEW_ROLE"},
            ],
        },
    )

    assert result["executed_queries"] == [
        'DROP ROLE "OLD_ROLE" CASCADE',
        'CREATE ROLE "NEW_ROLE"',
    ]


def test_ensure_init_secrets_are_not_exposed() -> None:
    """Verify passwords and LDAP distinguished names never appear in the result."""
    connection = FakeConnection()

    result = exasol_init.ensure_init(
        connection,
        {
            "users": [
                {"name": "SECRET_USER", "password": "Initial_Secret_42"},
                {
                    "name": "SECRET_LDAP_USER",
                    "authentication_method": "ldap",
                    "ldap_dn": "cn=secret,dc=authorization,dc=exasol,dc=com",
                },
            ]
        },
    )

    dumped = json.dumps(result)
    assert "Initial_Secret_42" not in dumped
    assert "cn=secret,dc=authorization,dc=exasol,dc=com" not in dumped


def test_ensure_schema_grant_rejects_invalid_privilege() -> None:
    """Verify unsupported privilege values fail before SQL generation."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match="privilege must be one of"):
        exasol_init.ensure_init(
            connection,
            {
                "grants": [
                    {
                        "schema": "APP_SCHEMA",
                        "privilege": "TRUNCATE",
                        "grantee": "APP_ROLE",
                    }
                ]
            },
        )


def test_module_argument_spec_exposes_every_phase() -> None:
    """Verify the Ansible-facing argument spec exposes all six phases."""
    argument_spec = exasol_init.module_argument_spec()

    assert set(argument_spec) >= {
        "roles",
        "users",
        "role_grants",
        "schemas",
        "grants",
        "scripts",
    }
    assert argument_spec["roles"]["options"]["name"]["required"] is True
    assert argument_spec["grants"]["options"]["privilege"]["choices"] == sorted(
        exasol_init.PRIVILEGES
    )
    assert argument_spec["scripts"] == {
        "type": "list",
        "elements": "str",
        "default": [],
    }


def test_run_init_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify init execution is routed through the runtime connection helper."""
    connection = object()
    params = {"roles": [{"name": "app_role"}]}

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_init.common_query,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_init,
        "ensure_init",
        lambda passed_connection, passed_params, check_mode=False: {
            "connection": passed_connection,
            "params": passed_params,
            "check_mode": check_mode,
        },
    )

    assert exasol_init.run_init(params, check_mode=True) == {
        "connection": connection,
        "params": params,
        "check_mode": True,
    }
