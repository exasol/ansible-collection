"""Tests for Exasol schema runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_schema
from exasol.ansible_modules.common_identifier_validation import (
    validate_schema_name,
)


class FakeStatement:
    """Small pyexasol statement stand-in for schema runtime tests."""

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
        schemas: set[str] | None = None,
    ) -> None:
        self.schemas = schemas or set()
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> FakeStatement:
        normalized_query = " ".join(query.split())

        self.executed.append(
            (
                normalized_query,
                query_params,
            )
        )

        if normalized_query.startswith("SELECT SCHEMA_NAME"):
            schema_name = str((query_params or {})["schema_name"])

            matched_schema = _matching_identifier(
                self.schemas,
                schema_name,
            )

            rows = []

            if matched_schema is not None:
                rows = [
                    {
                        "SCHEMA_NAME": matched_schema,
                    }
                ]

            return FakeStatement(
                rows=rows,
                rowcount=len(rows),
            )

        if normalized_query.startswith("CREATE SCHEMA"):
            self.schemas.add(
                _quoted_identifier(normalized_query),
            )

            return FakeStatement(
                result_type="rowCount",
            )

        if normalized_query.startswith("DROP SCHEMA"):
            schema_name = _quoted_identifier(normalized_query)

            matched_schema = _matching_identifier(
                self.schemas,
                schema_name,
            )

            if matched_schema is not None:
                self.schemas.remove(matched_schema)

            return FakeStatement(
                result_type="rowCount",
            )

        raise RuntimeError(f"unexpected query: {query}")


def test_ensure_schema_creates_missing_schema() -> None:
    """Verify missing schemas are created."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "present",
        },
    )

    assert result == {
        "changed": True,
        "schema": "SALES",
        "state": "present",
        "exists": True,
        "executed_queries": [
            'CREATE SCHEMA "SALES"',
        ],
    }

    assert "SALES" in connection.schemas


def test_ensure_schema_existing_schema_is_idempotent() -> None:
    """Verify existing schemas are not recreated."""
    connection = FakeConnection(
        schemas={"SALES"},
    )

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "present",
        },
    )

    assert result["changed"] is False
    assert result["exists"] is True
    assert result["executed_queries"] == []

    assert len(connection.executed) == 1


def test_ensure_schema_existing_schema_with_different_case_is_idempotent() -> None:
    """Verify regular identifiers use Exasol case-insensitive lookup."""
    connection = FakeConnection(
        schemas={"SALES"},
    )

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "sales",
            "state": "present",
        },
    )

    assert result["changed"] is False
    assert result["schema"] == "sales"
    assert result["exists"] is True
    assert result["executed_queries"] == []

    assert connection.schemas == {"SALES"}


def test_ensure_schema_absent_drops_existing_schema() -> None:
    """Verify existing schemas are removed."""
    connection = FakeConnection(
        schemas={"SALES"},
    )

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "absent",
        },
    )

    assert result == {
        "changed": True,
        "schema": "SALES",
        "state": "absent",
        "exists": False,
        "executed_queries": [
            'DROP SCHEMA "SALES"',
        ],
    }

    assert "SALES" not in connection.schemas


def test_ensure_schema_absent_drops_with_cascade() -> None:
    """Verify DROP SCHEMA CASCADE syntax."""
    connection = FakeConnection(
        schemas={"SALES"},
    )

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "absent",
            "cascade": True,
        },
    )

    assert result["changed"] is True

    assert result["executed_queries"] == [
        'DROP SCHEMA "SALES" CASCADE',
    ]

    assert "SALES" not in connection.schemas


def test_ensure_schema_missing_schema_absent_is_idempotent() -> None:
    """Verify dropping missing schemas does nothing."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "absent",
        },
    )

    assert result["changed"] is False
    assert result["exists"] is False
    assert result["executed_queries"] == []


def test_ensure_schema_check_mode_predicts_create_without_writing() -> None:
    """Verify check mode predicts creation."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "present",
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is True

    assert result["executed_queries"] == [
        'CREATE SCHEMA "SALES"',
    ]

    assert connection.schemas == set()


def test_ensure_schema_check_mode_predicts_drop_without_writing() -> None:
    """Verify check mode predicts dropping."""
    connection = FakeConnection(
        schemas={"SALES"},
    )

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "SALES",
            "state": "absent",
            "cascade": True,
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is False

    assert result["executed_queries"] == [
        'DROP SCHEMA "SALES" CASCADE',
    ]

    assert connection.schemas == {"SALES"}


@pytest.mark.parametrize(
    ("params", "message"),
    [
        (
            {
                "name": "",
                "state": "present",
            },
            "name must be a non-empty string",
        ),
        (
            {
                "name": "SALES",
                "state": "invalid",
            },
            "state must be one of",
        ),
        (
            {
                "name": "SALES\x00",
            },
            "must not contain NUL characters",
        ),
        (
            {
                "name": '"unterminated',
            },
            "malformed delimited identifier syntax",
        ),
    ],
)
def test_ensure_schema_rejects_invalid_parameters(
    params: dict[str, object],
    message: str,
) -> None:
    """Verify invalid schema lifecycle parameters fail."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match=message):
        exasol_schema.ensure_schema(
            connection,
            params,
        )


def test_schema_metadata_rejects_unexpected_row_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify metadata probing rejects unexpected query results."""

    def execute_queries(
        *_args: object,
        **_kwargs: object,
    ) -> dict[str, object]:
        return {
            "query_result": [
                ("SALES",),
            ],
        }

    monkeypatch.setattr(
        exasol_schema.common_query,
        "execute_queries",
        execute_queries,
    )

    with pytest.raises(
        ValueError,
        match="unexpected row",
    ):
        exasol_schema._schema_metadata(
            object(),
            "SALES",
        )


def test_normalized_error_message_delegates_schema_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify normalized errors delegate correctly."""

    def normalized_exasol_error_message(
        error: BaseException,
        *,
        params: dict[str, object],
        operation: str,
    ) -> str:
        assert str(error) == "failed"
        assert operation == "schema operation"
        assert params["name"] == "SALES"

        return "schema operation failed"

    monkeypatch.setattr(
        exasol_schema.common_query,
        "normalized_exasol_error_message",
        normalized_exasol_error_message,
    )

    assert (
        exasol_schema.normalized_exasol_error_message(
            RuntimeError("failed"),
            params={
                "name": "SALES",
            },
            operation="schema operation",
        )
        == "schema operation failed"
    )


def test_sanitize_error_message_redacts_password() -> None:
    """Verify schema errors sanitize sensitive connection values."""
    message = exasol_schema.sanitize_error_message(
        RuntimeError("failed near SALES password123"),
        {
            "login_password": "password123",
        },
    )

    assert message == "failed near SALES ********"


@pytest.mark.parametrize(
    "identifier",
    [
        object(),
        "",
        '"unterminated',
        '"bad"quote"',
        f"A{'B' * 128}",
    ],
)
def test_validate_schema_name_rejects_invalid_identifiers(
    identifier: object,
) -> None:
    """Verify schema names follow exact identifier rules."""
    with pytest.raises(ValueError):
        validate_schema_name(identifier)  # type: ignore[arg-type]


def test_validate_schema_name_accepts_regular_identifier() -> None:
    """Verify valid schema names pass validation."""
    assert validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"


def test_validate_schema_name_accepts_exact_identifier_with_special_characters() -> (
    None
):
    """Verify schema names accept exact identifier semantics like user/role."""
    assert validate_schema_name("App+/=Schema") == "App+/=Schema"
    assert validate_schema_name('"App+/=Schema"') == "App+/=Schema"


def _quoted_identifier(query: str) -> str:
    """Extract first quoted SQL identifier."""
    start = query.index('"')
    end = query.index('"', start + 1)

    return query[start + 1 : end]


def _matching_identifier(
    values: set[str],
    identifier: str,
) -> str | None:
    """Find identifier using Exasol case-insensitive comparison."""
    for value in values:
        if value.casefold() == identifier.casefold():
            return value

    return None
