"""Tests for Exasol grant runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_grants


class FakeStatement:
    """Small pyexasol statement stand-in for grant runtime tests."""

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
    """Small stateful pyexasol connection stand-in."""

    def __init__(
        self,
        system_grants: set[tuple[str, str, bool]] | None = None,
        object_grants: set[tuple[str, str, str, str | None]] | None = None,
        role_grants: set[tuple[str, str, bool]] | None = None,
    ) -> None:
        self.system_grants = system_grants or set()
        self.object_grants = object_grants or set()
        self.role_grants = role_grants or set()
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, query_params))
        params = query_params or {}

        if normalized_query.startswith(
            "SELECT PRIVILEGE, ADMIN_OPTION FROM EXA_DBA_SYS_PRIVS"
        ):
            return self._system_privilege_statement(params)

        if normalized_query.startswith("SELECT PRIVILEGE FROM EXA_DBA_OBJ_PRIVS"):
            return self._object_privilege_statement(params)

        if normalized_query.startswith(
            "SELECT GRANTED_ROLE, ADMIN_OPTION FROM EXA_DBA_ROLE_PRIVS"
        ):
            return self._role_grant_statement(params)

        if normalized_query.startswith("GRANT "):
            self._grant(normalized_query)
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("REVOKE "):
            self._revoke(normalized_query)
            return FakeStatement(result_type="rowCount")

        raise RuntimeError(f"unexpected query: {query}")

    def _system_privilege_statement(self, params: dict[str, Any]) -> FakeStatement:
        principal = str(params["principal"])
        privilege = str(params["privilege"])
        admin_option = _system_admin_option(self.system_grants, principal, privilege)
        rows = []
        if admin_option is not None:
            rows = [{"PRIVILEGE": privilege, "ADMIN_OPTION": admin_option}]
        return FakeStatement(rows=rows, rowcount=len(rows))

    def _object_privilege_statement(self, params: dict[str, Any]) -> FakeStatement:
        principal = str(params["principal"])
        privilege = str(params["privilege"])
        schema_name = str(params["schema_name"])
        object_name = params["object_name"]
        key = _object_key(
            principal,
            privilege,
            schema_name,
            str(object_name) if object_name is not None else None,
        )
        rows = [{"PRIVILEGE": privilege}] if key in self.object_grants else []
        return FakeStatement(rows=rows, rowcount=len(rows))

    def _role_grant_statement(self, params: dict[str, Any]) -> FakeStatement:
        principal = str(params["principal"])
        granted_role = str(params["granted_role"])
        admin_option = _role_admin_option(self.role_grants, principal, granted_role)
        rows = []
        if admin_option is not None:
            rows = [{"GRANTED_ROLE": granted_role, "ADMIN_OPTION": admin_option}]
        return FakeStatement(rows=rows, rowcount=len(rows))

    def _grant(self, query: str) -> None:
        if query.startswith("GRANT ") and " ON " not in query and " TO " in query:
            left_identifier_count = len(_quoted_identifiers(query.split(" TO ", 1)[0]))
            if left_identifier_count == 1:
                granted_role, principal = _role_statement_parts(
                    query,
                    "GRANT ",
                    " TO ",
                )
                self._discard_role_grant(principal, granted_role)
                self.role_grants.add(
                    _role_key(
                        principal,
                        granted_role,
                        _statement_admin_option(query),
                    )
                )
                return

        if " ON " not in query:
            privilege, principal = _system_statement_parts(query, "GRANT ", " TO ")
            self._discard_system_grant(principal, privilege)
            self.system_grants.add(
                _system_key(principal, privilege, _statement_admin_option(query))
            )
            return

        privilege, schema_name, object_name, principal = _object_statement_parts(
            query,
            "GRANT ",
            " TO ",
        )
        self.object_grants.add(
            _object_key(principal, privilege, schema_name, object_name)
        )

    def _revoke(self, query: str) -> None:
        if query.startswith("REVOKE ") and " ON " not in query and " FROM " in query:
            left_identifier_count = len(
                _quoted_identifiers(query.split(" FROM ", 1)[0])
            )
            if left_identifier_count == 1:
                granted_role, principal = _role_statement_parts(
                    query,
                    "REVOKE ",
                    " FROM ",
                )
                self._discard_role_grant(principal, granted_role)
                return

        if " ON " not in query:
            privilege, principal = _system_statement_parts(query, "REVOKE ", " FROM ")
            self._discard_system_grant(principal, privilege)
            return

        privilege, schema_name, object_name, principal = _object_statement_parts(
            query,
            "REVOKE ",
            " FROM ",
        )
        self.object_grants.discard(
            _object_key(principal, privilege, schema_name, object_name)
        )

    def _discard_system_grant(self, principal: str, privilege: str) -> None:
        self.system_grants = {
            grant
            for grant in self.system_grants
            if grant[:2] != _system_key(principal, privilege)[:2]
        }

    def _discard_role_grant(self, principal: str, granted_role: str) -> None:
        self.role_grants = {
            grant
            for grant in self.role_grants
            if grant[:2] != _role_key(principal, granted_role)[:2]
        }


def test_ensure_grants_grants_missing_system_privilege_to_user() -> None:
    """Verify a missing system privilege produces one GRANT statement."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["create   session"],
        },
    )

    assert result == {
        "changed": True,
        "principal": "app_user",
        "principal_type": "user",
        "state": "present",
        "executed_queries": ['GRANT CREATE SESSION TO "app_user"'],
    }
    assert _system_key("app_user", "CREATE SESSION") in connection.system_grants


# [utest -> dsn~authorization-state-reconciliation~1]
# [utest -> dsn~plan-authorization-lifecycle-sql-from-metadata~1]
# [utest -> dsn~derive-changed-from-planned-sql~1]
def test_ensure_grants_existing_system_privilege_is_unchanged() -> None:
    """Verify repeated system grants are idempotent."""
    connection = FakeConnection(
        system_grants={_system_key("APP_USER", "CREATE SESSION")}
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["CREATE SESSION"],
        },
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_grants_revokes_existing_schema_object_privilege() -> None:
    """Verify an existing schema-level object privilege is revoked."""
    connection = FakeConnection(
        object_grants={_object_key("app_role", "USAGE", "app_schema", None)}
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "role": "app_role",
            "state": "absent",
            "object_privileges": [
                {
                    "schema": "app_schema",
                    "privileges": ["USAGE"],
                }
            ],
        },
    )

    assert result == {
        "changed": True,
        "principal": "app_role",
        "principal_type": "role",
        "state": "absent",
        "executed_queries": ['REVOKE USAGE ON "APP_SCHEMA" FROM "app_role"'],
    }
    assert not connection.object_grants


def test_ensure_grants_grants_role_membership_to_user() -> None:
    """Verify a missing role membership produces one GRANT role statement."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": ["app_role"],
        },
    )

    assert result == {
        "changed": True,
        "principal": "app_user",
        "principal_type": "user",
        "state": "present",
        "executed_queries": ['GRANT "app_role" TO "app_user"'],
    }
    assert _role_key("app_user", "app_role") in connection.role_grants


def test_ensure_grants_grants_system_privilege_with_admin_option() -> None:
    """Verify admin_option grants system privileges with delegation rights."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["SELECT ANY TABLE"],
            "admin_option": True,
        },
    )

    assert result["executed_queries"] == [
        'GRANT SELECT ANY TABLE TO "app_user" WITH ADMIN OPTION'
    ]
    assert _system_key("app_user", "SELECT ANY TABLE", True) in (
        connection.system_grants
    )


def test_ensure_grants_grants_mixed_system_privilege_admin_options() -> None:
    """Verify each system privilege entry can choose admin_option."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": [
                {"privilege": "SELECT ANY TABLE", "admin_option": True},
                {"privilege": "CREATE SESSION", "admin_option": False},
            ],
        },
    )

    assert result["executed_queries"] == [
        'GRANT SELECT ANY TABLE TO "app_user" WITH ADMIN OPTION',
        'GRANT CREATE SESSION TO "app_user"',
    ]
    assert _system_key("app_user", "SELECT ANY TABLE", True) in (
        connection.system_grants
    )
    assert _system_key("app_user", "CREATE SESSION") in connection.system_grants


def test_ensure_grants_system_entry_admin_option_overrides_task_default() -> None:
    """Verify per-privilege admin_option overrides task-level admin_option."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": [
                {"privilege": "SELECT ANY TABLE", "admin_option": False},
                "CREATE SESSION",
            ],
            "admin_option": True,
        },
    )

    assert result["executed_queries"] == [
        'GRANT SELECT ANY TABLE TO "app_user"',
        'GRANT CREATE SESSION TO "app_user" WITH ADMIN OPTION',
    ]
    assert _system_key("app_user", "SELECT ANY TABLE") in connection.system_grants
    assert _system_key("app_user", "CREATE SESSION", True) in (connection.system_grants)


def test_ensure_grants_grants_role_membership_with_admin_option() -> None:
    """Verify admin_option grants role memberships with delegation rights."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": ["app_role"],
            "admin_option": True,
        },
    )

    assert result["executed_queries"] == [
        'GRANT "app_role" TO "app_user" WITH ADMIN OPTION'
    ]
    assert _role_key("app_user", "app_role", True) in connection.role_grants


def test_ensure_grants_grants_mixed_role_membership_admin_options() -> None:
    """Verify each role entry can choose its own admin_option value."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": [
                {"role": "app_reader", "admin_option": True},
                {"role": "app_writer", "admin_option": False},
            ],
        },
    )

    assert result["executed_queries"] == [
        'GRANT "app_reader" TO "app_user" WITH ADMIN OPTION',
        'GRANT "app_writer" TO "app_user"',
    ]
    assert _role_key("app_user", "app_reader", True) in connection.role_grants
    assert _role_key("app_user", "app_writer") in connection.role_grants


def test_ensure_grants_role_entry_admin_option_overrides_task_default() -> None:
    """Verify per-role admin_option overrides task-level admin_option."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": [
                {"role": "app_reader", "admin_option": False},
                "app_writer",
            ],
            "admin_option": True,
        },
    )

    assert result["executed_queries"] == [
        'GRANT "app_reader" TO "app_user"',
        'GRANT "app_writer" TO "app_user" WITH ADMIN OPTION',
    ]
    assert _role_key("app_user", "app_reader") in connection.role_grants
    assert _role_key("app_user", "app_writer", True) in connection.role_grants


def test_ensure_grants_upgrades_existing_system_privilege_to_admin_option() -> None:
    """Verify existing normal grants can be upgraded to admin option."""
    connection = FakeConnection(
        system_grants={_system_key("app_user", "SELECT ANY TABLE")}
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["SELECT ANY TABLE"],
            "admin_option": True,
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'GRANT SELECT ANY TABLE TO "app_user" WITH ADMIN OPTION'
    ]
    assert _system_key("app_user", "SELECT ANY TABLE", True) in (
        connection.system_grants
    )


def test_ensure_grants_downgrades_system_privilege_admin_option() -> None:
    """Verify admin_option=false reconciles an existing admin grant."""
    connection = FakeConnection(
        system_grants={_system_key("app_user", "SELECT ANY TABLE", True)}
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["SELECT ANY TABLE"],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'REVOKE SELECT ANY TABLE FROM "app_user"',
        'GRANT SELECT ANY TABLE TO "app_user"',
    ]
    assert _system_key("app_user", "SELECT ANY TABLE") in connection.system_grants
    assert _system_key("app_user", "SELECT ANY TABLE", True) not in (
        connection.system_grants
    )


def test_ensure_grants_downgrades_role_membership_admin_option() -> None:
    """Verify admin_option=false reconciles an existing role admin grant."""
    connection = FakeConnection(role_grants={_role_key("app_user", "app_role", True)})

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": ["app_role"],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'REVOKE "app_role" FROM "app_user"',
        'GRANT "app_role" TO "app_user"',
    ]
    assert _role_key("app_user", "app_role") in connection.role_grants
    assert _role_key("app_user", "app_role", True) not in connection.role_grants


def test_ensure_grants_existing_role_membership_is_unchanged() -> None:
    """Verify repeated role membership grants are idempotent."""
    connection = FakeConnection(role_grants={_role_key("APP_USER", "APP_ROLE")})

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": ["app_role"],
        },
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_grants_revokes_existing_role_membership() -> None:
    """Verify absent state revokes an existing role membership."""
    connection = FakeConnection(role_grants={_role_key("app_role", "nested_role")})

    result = exasol_grants.ensure_grants(
        connection,
        {
            "role": "app_role",
            "roles": ["nested_role"],
            "state": "absent",
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == ['REVOKE "nested_role" FROM "app_role"']
    assert not connection.role_grants


def test_ensure_grants_check_mode_predicts_role_membership_without_writing() -> None:
    """Verify check mode reports planned role grants without execution."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "roles": ["app_role"],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == ['GRANT "app_role" TO "app_user"']
    assert connection.role_grants == set()
    assert len(connection.executed) == 1


def test_ensure_grants_missing_schema_object_privilege_absent_is_unchanged() -> None:
    """Verify absent missing object grants are idempotent."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "role": "app_role",
            "state": "absent",
            "object_privileges": [
                {
                    "schema": "app_schema",
                    "privileges": ["USAGE"],
                }
            ],
        },
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_grants_grants_table_object_privilege() -> None:
    """Verify schema-qualified object targets are planned and stored."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "object_privileges": [
                {
                    "schema": "app_schema",
                    "object": "fact_sales",
                    "object_type": "table",
                    "privileges": ["SELECT"],
                }
            ],
        },
    )

    assert result["executed_queries"] == [
        'GRANT SELECT ON TABLE "APP_SCHEMA"."FACT_SALES" TO "app_user"'
    ]
    assert (
        _object_key("app_user", "SELECT", "app_schema", "fact_sales")
        in connection.object_grants
    )


def test_ensure_grants_handles_multiple_system_and_object_privileges() -> None:
    """Verify mixed multi-privilege requests are planned independently."""
    connection = FakeConnection(
        system_grants={_system_key("app_user", "CREATE SESSION")},
        object_grants={_object_key("app_user", "SELECT", "app_schema", "fact_sales")},
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["CREATE SESSION", "CREATE SCHEMA"],
            "object_privileges": [
                {
                    "schema": "app_schema",
                    "privileges": ["USAGE"],
                },
                {
                    "schema": "app_schema",
                    "object": "fact_sales",
                    "privileges": ["SELECT", "INSERT", "UPDATE"],
                },
            ],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'GRANT CREATE SCHEMA TO "app_user"',
        'GRANT USAGE ON "APP_SCHEMA" TO "app_user"',
        'GRANT INSERT ON "APP_SCHEMA"."FACT_SALES" TO "app_user"',
        'GRANT UPDATE ON "APP_SCHEMA"."FACT_SALES" TO "app_user"',
    ]
    assert _system_key("app_user", "CREATE SESSION") in connection.system_grants
    assert _system_key("app_user", "CREATE SCHEMA") in connection.system_grants
    assert _object_key("app_user", "USAGE", "app_schema", None) in (
        connection.object_grants
    )
    assert _object_key("app_user", "SELECT", "app_schema", "fact_sales") in (
        connection.object_grants
    )
    assert _object_key("app_user", "INSERT", "app_schema", "fact_sales") in (
        connection.object_grants
    )
    assert _object_key("app_user", "UPDATE", "app_schema", "fact_sales") in (
        connection.object_grants
    )


def test_ensure_grants_revokes_multiple_requested_privileges_only() -> None:
    """Verify absent state revokes each requested existing privilege only."""
    connection = FakeConnection(
        system_grants={
            _system_key("app_role", "CREATE SESSION"),
            _system_key("app_role", "CREATE SCHEMA"),
        },
        object_grants={
            _object_key("app_role", "USAGE", "app_schema", None),
            _object_key("app_role", "SELECT", "app_schema", "fact_sales"),
            _object_key("app_role", "INSERT", "app_schema", "fact_sales"),
        },
    )

    result = exasol_grants.ensure_grants(
        connection,
        {
            "role": "app_role",
            "state": "absent",
            "system_privileges": ["CREATE SCHEMA", "CREATE USER"],
            "object_privileges": [
                {
                    "schema": "app_schema",
                    "object": "fact_sales",
                    "privileges": ["INSERT", "UPDATE"],
                }
            ],
        },
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        'REVOKE CREATE SCHEMA FROM "app_role"',
        'REVOKE INSERT ON "APP_SCHEMA"."FACT_SALES" FROM "app_role"',
    ]
    assert _system_key("app_role", "CREATE SESSION") in connection.system_grants
    assert _system_key("app_role", "CREATE SCHEMA") not in connection.system_grants
    assert _system_key("app_role", "CREATE USER") not in connection.system_grants
    assert _object_key("app_role", "USAGE", "app_schema", None) in (
        connection.object_grants
    )
    assert _object_key("app_role", "SELECT", "app_schema", "fact_sales") in (
        connection.object_grants
    )
    assert _object_key("app_role", "INSERT", "app_schema", "fact_sales") not in (
        connection.object_grants
    )


# [utest -> dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1]
def test_ensure_grants_check_mode_predicts_without_writing() -> None:
    """Verify check mode reports planned GRANT statements without execution."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["CREATE SESSION"],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == ['GRANT CREATE SESSION TO "app_user"']
    assert connection.system_grants == set()
    assert len(connection.executed) == 1


@pytest.mark.parametrize(
    "params",
    [
        {"system_privileges": ["CREATE SESSION"]},
        {
            "user": "app_user",
            "role": "app_role",
            "system_privileges": ["CREATE SESSION"],
        },
    ],
)
def test_ensure_grants_rejects_invalid_principal_selection(
    params: dict[str, object],
) -> None:
    """Verify exactly one principal parameter is required."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match="exactly one"):
        exasol_grants.ensure_grants(connection, params)


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"user": "app_user"}, "at least one"),
        (
            {"user": "app_user", "system_privileges": ["DROP DATABASE"]},
            "unsupported Exasol system privilege",
        ),
        (
            {"user": "app_user", "system_privileges": [{"name": "CREATE SESSION"}]},
            "system privilege must be a non-empty string",
        ),
        (
            {
                "user": "app_user",
                "system_privileges": [
                    {"privilege": "CREATE SESSION", "admin_option": "true"}
                ],
            },
            r"system_privileges\[0\]\.admin_option must be a boolean",
        ),
        (
            {
                "user": "app_user",
                "system_privileges": ["CREATE SESSION"],
                "object_privileges": [],
            },
            "object_privileges must not be empty",
        ),
        (
            {"user": "app_user", "roles": []},
            "roles must not be empty",
        ),
        (
            {"user": "app_user", "roles": ['"app_role']},
            "malformed delimited identifier",
        ),
        (
            {"user": "app_user", "roles": [{"name": "app_role"}]},
            "role must be a non-empty string",
        ),
        (
            {
                "user": "app_user",
                "roles": [{"role": "app_role", "admin_option": "true"}],
            },
            r"roles\[0\]\.admin_option must be a boolean",
        ),
        (
            {
                "user": "app_user",
                "object_privileges": [{"schema": "app_schema", "privileges": ["READ"]}],
            },
            "unsupported Exasol object privilege",
        ),
        (
            {
                "user": "app_user",
                "object_privileges": [
                    {"schema": "app-schema", "privileges": ["USAGE"]}
                ],
            },
            "not a valid regular identifier",
        ),
        (
            {
                "user": "app_user",
                "object_privileges": [
                    {
                        "schema": "app_schema",
                        "object_type": "package",
                        "privileges": ["USAGE"],
                    }
                ],
            },
            "object_type must be one of",
        ),
        (
            {
                "user": "app_user",
                "object_privileges": [
                    {"schema": "app_schema", "privileges": ["USAGE"]}
                ],
                "admin_option": True,
            },
            "admin_option applies only",
        ),
        (
            {
                "user": "app_user",
                "system_privileges": ["CREATE SESSION"],
                "admin_option": "true",
            },
            "admin_option must be a boolean",
        ),
    ],
)
def test_ensure_grants_rejects_invalid_grant_parameters(
    params: dict[str, object],
    message: str,
) -> None:
    """Verify invalid grant parameters fail before write SQL generation."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match=message):
        exasol_grants.ensure_grants(connection, params)


def test_ensure_grants_accepts_delimited_principal_identifier() -> None:
    """Verify user and role values support exact delimited identifiers."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": '"App+/=User"',
            "system_privileges": ["CREATE SESSION"],
        },
    )

    assert result["principal"] == "App+/=User"
    assert result["executed_queries"] == ['GRANT CREATE SESSION TO "App+/=User"']


def test_ensure_grants_deduplicates_identical_requests() -> None:
    """Verify duplicate privilege requests do not produce duplicate statements."""
    connection = FakeConnection()

    result = exasol_grants.ensure_grants(
        connection,
        {
            "user": "app_user",
            "system_privileges": ["CREATE SESSION", "create session"],
        },
    )

    assert result["executed_queries"] == ['GRANT CREATE SESSION TO "app_user"']
    assert len(connection.executed) == 2


def test_module_argument_spec_exposes_grant_specific_options() -> None:
    """Verify the grants runtime exposes the full Ansible-facing argument spec."""
    argument_spec = exasol_grants.module_argument_spec()

    assert argument_spec["user"] == {"type": "str"}
    assert argument_spec["role"] == {"type": "str"}
    assert argument_spec["state"]["choices"] == ["absent", "present"]
    assert argument_spec["system_privileges"]["elements"] == "raw"
    assert argument_spec["roles"] == {"type": "list", "elements": "raw"}
    assert argument_spec["admin_option"] == {"type": "bool", "default": False}
    assert argument_spec["object_privileges"]["elements"] == "dict"
    assert (
        "schema"
        not in argument_spec["object_privileges"]["options"]["object_type"]["choices"]
    )
    assert argument_spec["object_privileges"]["options"]["privileges"] == {
        "type": "list",
        "elements": "str",
        "required": True,
    }


def test_grants_error_helpers_delegate_to_common_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify grant error helpers reuse the shared query sanitizer contract."""

    def sanitize_error_message(
        error: object,
        params: dict[str, object],
    ) -> str:
        assert str(error) == "grant failed secret"
        assert params == {"login_password": "secret"}
        return "grant failed ********"

    def normalized_exasol_error_message(
        error: BaseException,
        *,
        params: dict[str, object],
        operation: str,
    ) -> str:
        assert str(error) == "grant failed secret"
        assert params == {"login_password": "secret"}
        assert operation == "grant operation"
        return "grant operation failed: grant failed ********"

    monkeypatch.setattr(
        exasol_grants.common_query,
        "sanitize_error_message",
        sanitize_error_message,
    )
    monkeypatch.setattr(
        exasol_grants.common_query,
        "normalized_exasol_error_message",
        normalized_exasol_error_message,
    )

    assert (
        exasol_grants.sanitize_error_message(
            RuntimeError("grant failed secret"),
            {"login_password": "secret"},
        )
        == "grant failed ********"
    )
    assert (
        exasol_grants.normalized_exasol_error_message(
            RuntimeError("grant failed secret"),
            params={"login_password": "secret"},
            operation="grant operation",
        )
        == "grant operation failed: grant failed ********"
    )


def test_run_grants_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify grant execution is routed through the runtime connection helper."""
    connection = object()
    params = {"user": "app_user", "system_privileges": ["CREATE SESSION"]}

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_grants.common_query,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_grants,
        "ensure_grants",
        lambda passed_connection, passed_params, check_mode=False: {
            "connection": passed_connection,
            "params": passed_params,
            "check_mode": check_mode,
        },
    )

    assert exasol_grants.run_grants(params, check_mode=True) == {
        "connection": connection,
        "params": params,
        "check_mode": True,
    }


def _system_statement_parts(
    query: str,
    prefix: str,
    principal_separator: str,
) -> tuple[str, str]:
    body = query.removeprefix(prefix)
    privilege, principal_part = body.split(principal_separator, 1)
    return privilege, _quoted_identifiers(principal_part)[0]


def _object_statement_parts(
    query: str,
    prefix: str,
    principal_separator: str,
) -> tuple[str, str, str | None, str]:
    body = query.removeprefix(prefix)
    privilege, rest = body.split(" ON ", 1)
    target_part, principal_part = rest.split(principal_separator, 1)
    target_identifiers = _quoted_identifiers(target_part)
    principal = _quoted_identifiers(principal_part)[0]

    if len(target_identifiers) == 1:
        return privilege, target_identifiers[0], None, principal

    return privilege, target_identifiers[0], target_identifiers[1], principal


def _role_statement_parts(
    query: str,
    prefix: str,
    principal_separator: str,
) -> tuple[str, str]:
    body = query.removeprefix(prefix)
    granted_role_part, principal_part = body.split(principal_separator, 1)
    return (
        _quoted_identifiers(granted_role_part)[0],
        _quoted_identifiers(principal_part)[0],
    )


def _quoted_identifiers(query: str) -> list[str]:
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


def _system_key(
    principal: str,
    privilege: str,
    admin_option: bool = False,
) -> tuple[str, str, bool]:
    return principal.casefold(), privilege.upper(), admin_option


def _role_key(
    principal: str,
    granted_role: str,
    admin_option: bool = False,
) -> tuple[str, str, bool]:
    return principal.casefold(), granted_role.casefold(), admin_option


def _system_admin_option(
    grants: set[tuple[str, str, bool]],
    principal: str,
    privilege: str,
) -> bool | None:
    key = _system_key(principal, privilege)
    matches = [
        admin_option for *grant, admin_option in grants if tuple(grant) == key[:2]
    ]
    if not matches:
        return None

    return matches[0]


def _role_admin_option(
    grants: set[tuple[str, str, bool]],
    principal: str,
    granted_role: str,
) -> bool | None:
    key = _role_key(principal, granted_role)
    matches = [
        admin_option for *grant, admin_option in grants if tuple(grant) == key[:2]
    ]
    if not matches:
        return None

    return matches[0]


def _statement_admin_option(query: str) -> bool:
    return query.endswith(" WITH ADMIN OPTION")


def _object_key(
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
