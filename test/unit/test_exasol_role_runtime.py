"""Tests for Exasol role runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_role
from exasol.ansible_modules.common_identifier_validation import validate_role_name


class FakeStatement:
    """Small pyexasol statement stand-in for role runtime tests."""

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

    def __init__(self, roles: set[str] | None = None) -> None:
        self.roles = roles or set()
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, query_params))

        if normalized_query.startswith("SELECT ROLE_NAME FROM EXA_ALL_ROLES"):
            role_name = str((query_params or {})["role_name"]).upper()
            rows = [{"ROLE_NAME": role_name}] if role_name in self.roles else []
            return FakeStatement(rows=rows, rowcount=len(rows))

        if normalized_query.startswith("CREATE ROLE"):
            self.roles.add(_quoted_identifier(normalized_query))
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("DROP ROLE"):
            self.roles.discard(_quoted_identifier(normalized_query))
            return FakeStatement(result_type="rowCount")

        raise RuntimeError(f"unexpected query: {query}")


def test_ensure_role_creates_missing_role() -> None:
    """Verify missing roles are created."""
    connection = FakeConnection()

    result = exasol_role.ensure_role(connection, {"name": "app_role"})

    assert result == {
        "changed": True,
        "role": "APP_ROLE",
        "state": "present",
        "exists": True,
        "executed_queries": ['CREATE ROLE "APP_ROLE"'],
    }
    assert "APP_ROLE" in connection.roles


def test_ensure_role_existing_role_is_unchanged() -> None:
    """Verify existing roles are idempotent."""
    connection = FakeConnection(roles={"APP_ROLE"})

    result = exasol_role.ensure_role(connection, {"name": "app_role"})

    assert result["changed"] is False
    assert result["exists"] is True
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_role_absent_drops_existing_role_with_cascade() -> None:
    """Verify absent roles are dropped only when they currently exist."""
    connection = FakeConnection(roles={"APP_ROLE"})

    result = exasol_role.ensure_role(
        connection,
        {"name": "app_role", "state": "absent", "cascade": True},
    )

    assert result == {
        "changed": True,
        "role": "APP_ROLE",
        "state": "absent",
        "exists": False,
        "executed_queries": ['DROP ROLE "APP_ROLE" CASCADE'],
    }
    assert "APP_ROLE" not in connection.roles


def test_ensure_role_missing_role_absent_is_unchanged() -> None:
    """Verify absent missing roles are idempotent."""
    connection = FakeConnection()

    result = exasol_role.ensure_role(
        connection,
        {"name": "app_role", "state": "absent"},
    )

    assert result["changed"] is False
    assert result["exists"] is False
    assert result["executed_queries"] == []
    assert len(connection.executed) == 1


def test_ensure_role_check_mode_predicts_create_without_writing() -> None:
    """Verify check mode does not execute planned CREATE ROLE statements."""
    connection = FakeConnection()

    result = exasol_role.ensure_role(
        connection,
        {"name": "app_role"},
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is True
    assert result["executed_queries"] == ['CREATE ROLE "APP_ROLE"']
    assert connection.roles == set()
    assert len(connection.executed) == 1


def test_ensure_role_check_mode_predicts_drop_without_writing() -> None:
    """Verify check mode does not execute planned DROP ROLE statements."""
    connection = FakeConnection(roles={"APP_ROLE"})

    result = exasol_role.ensure_role(
        connection,
        {"name": "app_role", "state": "absent", "cascade": True},
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is False
    assert result["executed_queries"] == ['DROP ROLE "APP_ROLE" CASCADE']
    assert connection.roles == {"APP_ROLE"}
    assert len(connection.executed) == 1


@pytest.mark.parametrize("role_name", ["bad-role", "", object()])
def test_ensure_role_rejects_invalid_role_names(role_name: object) -> None:
    """Verify invalid role names fail before SQL generation."""
    with pytest.raises(ValueError):
        exasol_role.ensure_role(FakeConnection(), {"name": role_name})


@pytest.mark.parametrize(
    "role_name",
    [object(), "", f"A{'B' * 128}", "bad-role"],
)
def test_validate_role_name_rejects_invalid_role_names(role_name: object) -> None:
    """Verify role-name validation rejects each invalid input class directly."""
    with pytest.raises(ValueError):
        validate_role_name(role_name)  # type: ignore[arg-type]


def test_ensure_role_rejects_invalid_state() -> None:
    """Verify invalid lifecycle state values fail before role probing."""
    with pytest.raises(ValueError, match="state must be one of"):
        exasol_role.ensure_role(
            FakeConnection(),
            {"name": "app_role", "state": "invalid"},
        )


def test_role_error_helpers_delegate_to_common_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify role error helpers reuse the shared query sanitizer contract."""

    def sanitize_error_message(
        error: object,
        params: dict[str, object],
    ) -> str:
        assert str(error) == "role failed secret"
        assert params == {"login_password": "secret"}
        return "role failed ********"

    def normalized_exasol_error_message(
        error: BaseException,
        *,
        params: dict[str, object],
        operation: str,
    ) -> str:
        assert str(error) == "role failed secret"
        assert params == {"login_password": "secret"}
        assert operation == "role operation"
        return "role operation failed: role failed ********"

    monkeypatch.setattr(
        exasol_role.common_query,
        "sanitize_error_message",
        sanitize_error_message,
    )
    monkeypatch.setattr(
        exasol_role.common_query,
        "normalized_exasol_error_message",
        normalized_exasol_error_message,
    )

    assert (
        exasol_role.sanitize_error_message(
            RuntimeError("role failed secret"),
            {"login_password": "secret"},
        )
        == "role failed ********"
    )
    assert (
        exasol_role.normalized_exasol_error_message(
            RuntimeError("role failed secret"),
            params={"login_password": "secret"},
            operation="role operation",
        )
        == "role operation failed: role failed ********"
    )


def _quoted_identifier(query: str) -> str:
    return query.split('"', 2)[1]
