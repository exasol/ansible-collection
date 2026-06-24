"""Tests for Exasol user runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_user
from exasol.ansible_modules.common_identifier_validation import validate_identifier


class FakeStatement:
    """Small pyexasol statement stand-in for user runtime tests."""

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
        users: set[str] | None = None,
        ldap_dns: dict[str, str] | None = None,
    ) -> None:
        self.users = users or set()
        self.ldap_dns = ldap_dns or {}
        self.grantees: set[str] = set()
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, query_params))

        if normalized_query.startswith("SELECT USER_NAME, DISTINGUISHED_NAME"):
            user_name = str((query_params or {})["user_name"]).upper()
            rows = (
                [
                    {
                        "USER_NAME": user_name,
                        "DISTINGUISHED_NAME": self.ldap_dns.get(user_name),
                    }
                ]
                if user_name in self.users
                else []
            )
            return FakeStatement(rows=rows, rowcount=len(rows))

        if normalized_query.startswith("CREATE USER"):
            self.users.add(_quoted_identifier(normalized_query))
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("GRANT CREATE SESSION TO"):
            self.grantees.add(_quoted_identifier(normalized_query))
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("ALTER USER"):
            user_name = _quoted_identifier(normalized_query)
            if "IDENTIFIED AT LDAP AS" in normalized_query:
                self.ldap_dns[user_name] = normalized_query.rsplit(" AS ", 1)[1].strip(
                    "'"
                )
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("DROP USER"):
            self.users.discard(_quoted_identifier(normalized_query))
            return FakeStatement(result_type="rowCount")

        raise RuntimeError(f"unexpected query: {query}")


def test_quote_password_identifier_preserves_case_and_escapes_quotes() -> None:
    """Verify passwords are quoted for Exasol IDENTIFIED BY syntax."""
    assert exasol_user._quote_password_identifier('h12_X"hz') == '"h12_X""hz"'


@pytest.mark.parametrize("password", ["", "bad\x00password", object()])
def test_quote_password_identifier_rejects_invalid_values(password: object) -> None:
    """Verify invalid passwords are rejected before SQL generation."""
    with pytest.raises(ValueError):
        exasol_user._quote_password_identifier(password)  # type: ignore[arg-type]


def test_ensure_user_creates_missing_user_and_grants_session() -> None:
    """Verify missing users are created and CREATE SESSION is granted."""
    connection = FakeConnection()

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "password": "h12_Xhz"},
    )

    assert result == {
        "changed": True,
        "user": "APP_USER",
        "state": "present",
        "exists": True,
        "executed_queries": [
            'CREATE USER "APP_USER" IDENTIFIED BY "********"',
            'GRANT CREATE SESSION TO "APP_USER"',
        ],
    }
    assert "APP_USER" in connection.users
    assert "APP_USER" in connection.grantees
    assert connection.executed[1][0] == 'CREATE USER "APP_USER" IDENTIFIED BY "h12_Xhz"'


def test_ensure_user_creates_missing_ldap_user() -> None:
    """Verify LDAP authentication can be used when creating a missing user."""
    connection = FakeConnection()

    result = exasol_user.ensure_user(
        connection,
        {
            "name": "app_user",
            "authentication_method": "ldap",
            "ldap_dn": "cn=app_user,dc=authorization,dc=exasol,dc=com",
        },
    )

    assert result == {
        "changed": True,
        "user": "APP_USER",
        "state": "present",
        "exists": True,
        "executed_queries": [
            "CREATE USER \"APP_USER\" IDENTIFIED AT LDAP AS '********'",
            'GRANT CREATE SESSION TO "APP_USER"',
        ],
    }
    assert connection.executed[1][0] == (
        'CREATE USER "APP_USER" IDENTIFIED AT LDAP AS '
        "'cn=app_user,dc=authorization,dc=exasol,dc=com'"
    )


def test_ensure_user_existing_on_create_password_mode_is_unchanged() -> None:
    """Verify existing users are idempotent with update_password=on_create."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "update_password": "on_create"},
    )

    assert result["changed"] is False
    assert result["exists"] is True
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_user_alters_existing_password_when_requested() -> None:
    """Verify update_password=always plans a password change for existing users."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {
            "name": "app_user",
            "password": "new-secret",
            "update_password": "always",
        },
    )

    assert result == {
        "changed": True,
        "user": "APP_USER",
        "state": "present",
        "exists": True,
        "executed_queries": ['ALTER USER "APP_USER" IDENTIFIED BY "********"'],
    }
    assert connection.executed[1][0] == (
        'ALTER USER "APP_USER" IDENTIFIED BY "new-secret"'
    )


def test_ensure_user_changes_existing_user_to_ldap() -> None:
    """Verify LDAP authentication updates generate Exasol LDAP syntax."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {
            "name": "app_user",
            "authentication_method": "ldap",
            "ldap_dn": "cn=app_user,dc=authorization,dc=exasol,dc=com",
        },
    )

    assert result == {
        "changed": True,
        "user": "APP_USER",
        "state": "present",
        "exists": True,
        "executed_queries": [
            "ALTER USER \"APP_USER\" IDENTIFIED AT LDAP AS '********'"
        ],
    }
    assert connection.executed[1][0] == (
        'ALTER USER "APP_USER" IDENTIFIED AT LDAP AS '
        "'cn=app_user,dc=authorization,dc=exasol,dc=com'"
    )


def test_ensure_user_existing_ldap_authentication_is_unchanged() -> None:
    """Verify matching LDAP distinguished names are idempotent."""
    ldap_dn = "cn=app_user,dc=authorization,dc=exasol,dc=com"
    connection = FakeConnection(users={"APP_USER"}, ldap_dns={"APP_USER": ldap_dn})

    result = exasol_user.ensure_user(
        connection,
        {
            "name": "app_user",
            "authentication_method": "ldap",
            "ldap_dn": ldap_dn,
        },
    )

    assert result["changed"] is False
    assert result["exists"] is True
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_user_absent_drops_existing_user_with_cascade() -> None:
    """Verify absent users are dropped only when they currently exist."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "state": "absent", "cascade": True},
    )

    assert result == {
        "changed": True,
        "user": "APP_USER",
        "state": "absent",
        "exists": False,
        "executed_queries": ['DROP USER "APP_USER" CASCADE'],
    }
    assert "APP_USER" not in connection.users


def test_ensure_user_missing_user_absent_is_unchanged() -> None:
    """Verify absent missing users are idempotent."""
    connection = FakeConnection()

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "state": "absent"},
    )

    assert result["changed"] is False
    assert result["exists"] is False
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_user_check_mode_predicts_without_writing() -> None:
    """Verify check mode does not execute planned CREATE/GRANT statements."""
    connection = FakeConnection()

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "password": "h12_Xhz"},
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is True
    assert result["executed_queries"] == [
        'CREATE USER "APP_USER" IDENTIFIED BY "********"',
        'GRANT CREATE SESSION TO "APP_USER"',
    ]
    assert connection.users == set()
    assert len(connection.executed) == 1


def test_ensure_user_check_mode_predicts_ldap_update_without_writing() -> None:
    """Verify check mode does not execute planned LDAP ALTER statements."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {
            "name": "app_user",
            "authentication_method": "ldap",
            "ldap_dn": "cn=app_user,dc=authorization,dc=exasol,dc=com",
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is True
    assert result["executed_queries"] == [
        "ALTER USER \"APP_USER\" IDENTIFIED AT LDAP AS '********'"
    ]
    assert connection.ldap_dns == {}
    assert len(connection.executed) == 1


def test_ensure_user_check_mode_predicts_drop_without_writing() -> None:
    """Verify check mode does not execute planned DROP statements."""
    connection = FakeConnection(users={"APP_USER"})

    result = exasol_user.ensure_user(
        connection,
        {"name": "app_user", "state": "absent", "cascade": True},
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is False
    assert result["executed_queries"] == ['DROP USER "APP_USER" CASCADE']
    assert connection.users == {"APP_USER"}
    assert len(connection.executed) == 1


def test_ensure_user_missing_password_for_create_fails() -> None:
    """Verify a missing user requires a password to be created."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match="password is required to create"):
        exasol_user.ensure_user(connection, {"name": "app_user"})


def test_ensure_user_missing_password_for_alter_fails() -> None:
    """Verify update_password=always requires a password for existing users."""
    connection = FakeConnection(users={"APP_USER"})

    with pytest.raises(ValueError, match="password is required to alter"):
        exasol_user.ensure_user(
            connection,
            {"name": "app_user", "update_password": "always"},
        )


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"name": "app_user", "state": "invalid"}, "state must be one of"),
        (
            {"name": "app_user", "update_password": "never"},
            "update_password must be one of",
        ),
        (
            {"name": "app_user", "authentication_method": "kerberos"},
            "authentication_method must be one of",
        ),
        ({"name": ""}, "name must be a non-empty string"),
        (
            {"name": "app_user", "authentication_method": "ldap"},
            "ldap_dn is required",
        ),
    ],
)
def test_ensure_user_rejects_invalid_lifecycle_parameters(
    params: dict[str, object],
    message: str,
) -> None:
    """Verify invalid lifecycle arguments fail before SQL generation."""
    with pytest.raises(ValueError, match=message):
        exasol_user.ensure_user(FakeConnection(users={"APP_USER"}), params)


def test_user_metadata_rejects_unexpected_row_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify metadata probing fails clearly when the query result shape is wrong."""

    def execute_queries(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"query_result": [("APP_USER", None)]}

    monkeypatch.setattr(exasol_user.common_query, "execute_queries", execute_queries)

    with pytest.raises(ValueError, match="unexpected row"):
        exasol_user._user_metadata(object(), "app_user")


def test_normalized_error_message_redacts_user_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify normalized user errors delegate with the expanded secret set."""

    def normalized_exasol_error_message(
        error: BaseException,
        *,
        params: dict[str, object],
        operation: str,
    ) -> str:
        assert str(error) == "failed near secret and cn=''app"
        assert operation == "user operation"
        assert params["password"] == "secret"
        assert params["ldap_dn"] == "cn='app"
        assert params["named_args"] == {
            "password": "secret",
            "password_sql_identifier": "secret",
            "ldap_dn": "cn='app",
            "ldap_dn_sql_literal": "cn=''app",
            "ldap_dn_secret": "cn='app",
            "ldap_dn_sql_literal_secret": "cn=''app",
        }
        return "user operation failed: failed near ******** and ********"

    monkeypatch.setattr(
        exasol_user.common_query,
        "normalized_exasol_error_message",
        normalized_exasol_error_message,
    )

    assert (
        exasol_user.normalized_exasol_error_message(
            RuntimeError("failed near secret and cn=''app"),
            params={"password": "secret", "ldap_dn": "cn='app"},
            operation="user operation",
        )
        == "user operation failed: failed near ******** and ********"
    )


def test_sanitize_error_message_redacts_user_password() -> None:
    """Verify user password values are treated as sensitive."""
    message = exasol_user.sanitize_error_message(
        RuntimeError('failed near h12_X"hz and h12_X""hz'),
        {"password": 'h12_X"hz'},
    )

    assert message == "failed near ******** and ********"


def test_sanitize_error_message_redacts_ldap_dn() -> None:
    """Verify LDAP distinguished names are treated as sensitive values."""
    message = exasol_user.sanitize_error_message(
        RuntimeError("failed near cn='app_user and cn=''app_user"),
        {"ldap_dn": "cn='app_user"},
    )

    assert message == "failed near ******** and ********"


@pytest.mark.parametrize("identifier", [object(), ""])
def test_validate_identifier_rejects_invalid_name_types(identifier: object) -> None:
    """Verify identifier validation rejects non-string and empty values directly."""
    with pytest.raises(ValueError):
        validate_identifier(identifier)  # type: ignore[arg-type]


@pytest.mark.parametrize("ldap_dn", [object(), "", "bad\x00dn"])
def test_quote_sql_string_literal_rejects_invalid_values(ldap_dn: object) -> None:
    """Verify invalid LDAP distinguished names fail before SQL generation."""
    with pytest.raises(ValueError):
        exasol_user._quote_sql_string_literal(ldap_dn)  # type: ignore[arg-type]


def test_quote_sql_string_literal_escapes_single_quotes() -> None:
    """Verify LDAP distinguished names are escaped as SQL string literals."""
    assert exasol_user._quote_sql_string_literal("cn=o'hara") == "'cn=o''hara'"


def _quoted_identifier(query: str) -> str:
    return query.split('"', 2)[1]
