"""Tests for Exasol schema runtime behavior."""

from __future__ import annotations

from typing import Any

import pytest

from exasol.ansible_modules import exasol_schema
from exasol.ansible_modules.common_identifier_validation import validate_schema_name


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
        *,
        owners: dict[str, str] | None = None,
        comments: dict[str, str | None] | None = None,
        raw_size_limits: dict[str, int | None] | None = None,
    ) -> None:
        self.schemas = schemas or set()
        self.owners = owners or {}
        self.comments = comments or {}
        self.raw_size_limits = raw_size_limits or {}
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(
        self, query: str, query_params: dict[str, Any] | None = None
    ) -> FakeStatement:
        normalized_query = " ".join(query.split())

        self.executed.append((normalized_query, query_params))

        if normalized_query.startswith("SELECT S.SCHEMA_NAME"):
            schema_name = str((query_params or {})["schema_name"])

            matched_schema = _matching_identifier(self.schemas, schema_name)

            rows = []

            if matched_schema is not None:
                rows = [
                    {
                        "SCHEMA_NAME": matched_schema,
                        "SCHEMA_OWNER": self.owners.get(matched_schema, "SYS"),
                        "SCHEMA_COMMENT": self.comments.get(matched_schema),
                        "RAW_SIZE_LIMIT": self.raw_size_limits.get(matched_schema),
                    }
                ]

            return FakeStatement(rows=rows, rowcount=len(rows))

        if normalized_query.startswith("CREATE SCHEMA"):
            self.schemas.add(_quoted_identifier(normalized_query))

            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("RENAME SCHEMA"):
            old_name, new_name = _quoted_identifiers(normalized_query)
            matched_schema = _matching_identifier(self.schemas, old_name)
            if matched_schema is not None:
                self.schemas.remove(matched_schema)
                self.schemas.add(new_name)
                _move_metadata(self.owners, matched_schema, new_name)
                _move_metadata(self.comments, matched_schema, new_name)
                _move_metadata(self.raw_size_limits, matched_schema, new_name)
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("COMMENT ON SCHEMA"):
            schema_name = _quoted_identifier(normalized_query)
            self.comments[schema_name] = _sql_comment(normalized_query)
            return FakeStatement(result_type="rowCount")

        if " SET RAW_SIZE_LIMIT = " in normalized_query:
            schema_name = _quoted_identifier(normalized_query)
            self.raw_size_limits[schema_name] = int(normalized_query.rsplit(" ", 1)[1])
            return FakeStatement(result_type="rowCount")

        if " CHANGE OWNER " in normalized_query:
            schema_name, owner = _quoted_identifiers(normalized_query)
            self.owners[schema_name] = owner
            return FakeStatement(result_type="rowCount")

        if normalized_query.startswith("DROP SCHEMA"):
            schema_name = _quoted_identifier(normalized_query)

            matched_schema = _matching_identifier(self.schemas, schema_name)

            if matched_schema is not None:
                self.schemas.remove(matched_schema)

            return FakeStatement(result_type="rowCount")

        raise RuntimeError(f"unexpected query: {query}")


def test_ensure_schema_creates_missing_schema() -> None:
    """Verify missing schemas are created."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "present"}
    )

    assert result == {
        "changed": True,
        "schema": "SALES",
        "state": "present",
        "exists": True,
        "executed_queries": ['CREATE SCHEMA "SALES"'],
    }

    assert "SALES" in connection.schemas


def test_module_argument_spec_exposes_schema_specific_options() -> None:
    """Verify the schema runtime exposes the Ansible-facing argument spec."""
    argument_spec = exasol_schema.module_argument_spec()

    assert argument_spec["name"] == {
        "type": "str",
        "required": True,
        "aliases": ["schema"],
    }
    assert argument_spec["state"]["choices"] == ["absent", "present"]
    assert argument_spec["state"]["default"] == "present"
    assert argument_spec["cascade"]["default"] is False
    assert argument_spec["owner"] == {"type": "str"}
    assert argument_spec["comment"] == {"type": "str"}
    assert argument_spec["new_name"] == {"type": "str"}
    assert argument_spec["raw_size_limit"] == {"type": "int"}


def test_ensure_schema_creates_schema_then_changes_owner() -> None:
    """Verify Exasol ownership is assigned after schema creation."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "owner": "APP_USER"}
    )

    assert result["executed_queries"] == [
        'CREATE SCHEMA "SALES"',
        'ALTER SCHEMA "SALES" CHANGE OWNER "APP_USER"',
    ]
    assert connection.owners["SALES"] == "APP_USER"


def test_ensure_schema_reconciles_owner() -> None:
    """Verify owner drift is reconciled."""
    connection = FakeConnection(schemas={"SALES"}, owners={"SALES": "OLD_USER"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "owner": "NEW_USER"}
    )

    assert result["executed_queries"] == [
        'ALTER SCHEMA "SALES" CHANGE OWNER "NEW_USER"'
    ]
    assert connection.owners["SALES"] == "NEW_USER"


def test_ensure_schema_matching_owner_is_idempotent() -> None:
    """Verify a matching owner does not produce SQL."""
    connection = FakeConnection(schemas={"SALES"}, owners={"SALES": "APP_USER"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "owner": "app_user"}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


def test_ensure_schema_reconciles_comment() -> None:
    """Verify schema comments are quoted and reconciled."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "comment": "Sales team's data"}
    )

    assert result["executed_queries"] == [
        "COMMENT ON SCHEMA \"SALES\" IS 'Sales team''s data'"
    ]
    assert connection.comments["SALES"] == "Sales team's data"


def test_ensure_schema_clears_comment() -> None:
    """Verify an empty requested comment removes the current comment."""
    connection = FakeConnection(schemas={"SALES"}, comments={"SALES": "Obsolete"})

    result = exasol_schema.ensure_schema(connection, {"name": "SALES", "comment": ""})

    assert result["executed_queries"] == ['COMMENT ON SCHEMA "SALES" IS NULL']
    assert connection.comments["SALES"] is None


def test_ensure_schema_renames_existing_schema() -> None:
    """Verify an existing schema can be renamed."""
    connection = FakeConnection(schemas={"OLD_NAME"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "OLD_NAME", "new_name": "NEW_NAME"}
    )

    assert result["schema"] == "NEW_NAME"
    assert result["executed_queries"] == ['RENAME SCHEMA "OLD_NAME" TO "NEW_NAME"']
    assert connection.schemas == {"NEW_NAME"}


def test_ensure_schema_rename_is_idempotent_after_rename() -> None:
    """Verify the desired rename target is recognized on repeated runs."""
    connection = FakeConnection(schemas={"NEW_NAME"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "OLD_NAME", "new_name": "NEW_NAME"}
    )

    assert result["changed"] is False
    assert result["schema"] == "NEW_NAME"


def test_ensure_schema_reconciles_raw_size_limit() -> None:
    """Verify schema quota drift is reconciled in bytes."""
    connection = FakeConnection(schemas={"SALES"}, raw_size_limits={"SALES": 1024})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "raw_size_limit": 2048}
    )

    assert result["executed_queries"] == [
        'ALTER SCHEMA "SALES" SET RAW_SIZE_LIMIT = 2048'
    ]
    assert connection.raw_size_limits["SALES"] == 2048


def test_ensure_schema_matching_raw_size_limit_is_idempotent() -> None:
    """Verify a matching quota does not produce SQL."""
    connection = FakeConnection(schemas={"SALES"}, raw_size_limits={"SALES": 2048})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "raw_size_limit": 2048}
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


def test_ensure_schema_plans_owner_last_after_other_properties() -> None:
    """Verify ownership transfer cannot remove access before other updates."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection,
        {
            "name": "OLD_NAME",
            "new_name": "NEW_NAME",
            "comment": "Sales",
            "raw_size_limit": 2048,
            "owner": "APP_ROLE",
        },
        check_mode=True,
    )

    assert result["executed_queries"] == [
        'CREATE SCHEMA "NEW_NAME"',
        "COMMENT ON SCHEMA \"NEW_NAME\" IS 'Sales'",
        'ALTER SCHEMA "NEW_NAME" SET RAW_SIZE_LIMIT = 2048',
        'ALTER SCHEMA "NEW_NAME" CHANGE OWNER "APP_ROLE"',
    ]
    assert connection.schemas == set()


def test_ensure_schema_rejects_rename_when_source_and_target_exist() -> None:
    """Verify ambiguous rename state fails without writing."""
    connection = FakeConnection(schemas={"OLD_NAME", "NEW_NAME"})

    with pytest.raises(ValueError, match="both identify existing schemas"):
        exasol_schema.ensure_schema(
            connection, {"name": "OLD_NAME", "new_name": "NEW_NAME"}
        )


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"name": "SALES", "owner": 1}, "owner must be a string"),
        ({"name": "SALES", "comment": 1}, "comment must be a string"),
        (
            {"name": "SALES", "comment": "x" * 2001},
            "comment must not exceed 2000 characters",
        ),
        ({"name": "SALES", "comment": "bad\x00value"}, "NUL characters"),
        (
            {"name": "SALES", "raw_size_limit": -1},
            "raw_size_limit must be a non-negative integer",
        ),
        (
            {"name": "SALES", "raw_size_limit": True},
            "raw_size_limit must be a non-negative integer",
        ),
        (
            {"name": "SALES", "state": "absent", "owner": "APP_ROLE"},
            "owner can only be used with state=present",
        ),
    ],
)
def test_ensure_schema_rejects_invalid_property_parameters(
    params: dict[str, object], message: str
) -> None:
    """Verify invalid mutable schema options fail before DDL."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match=message):
        exasol_schema.ensure_schema(connection, params)


def test_ensure_schema_existing_schema_is_idempotent() -> None:
    """Verify existing schemas are not recreated."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "present"}
    )

    assert result["changed"] is False
    assert result["exists"] is True
    assert result["executed_queries"] == []

    assert len(connection.executed) == 1


def test_ensure_schema_existing_schema_with_different_case_is_idempotent() -> None:
    """Verify regular identifiers use Exasol case-insensitive lookup."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "sales", "state": "present"}
    )

    assert result["changed"] is False
    assert result["schema"] == "sales"
    assert result["exists"] is True
    assert result["executed_queries"] == []

    assert connection.schemas == {"SALES"}


def test_ensure_schema_absent_drops_existing_schema() -> None:
    """Verify existing schemas are removed."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "absent"}
    )

    assert result == {
        "changed": True,
        "schema": "SALES",
        "state": "absent",
        "exists": False,
        "executed_queries": ['DROP SCHEMA "SALES"'],
    }

    assert "SALES" not in connection.schemas


def test_ensure_schema_absent_drops_with_cascade() -> None:
    """Verify DROP SCHEMA CASCADE syntax."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "absent", "cascade": True}
    )

    assert result["changed"] is True

    assert result["executed_queries"] == ['DROP SCHEMA "SALES" CASCADE']

    assert "SALES" not in connection.schemas


def test_ensure_schema_missing_schema_absent_is_idempotent() -> None:
    """Verify dropping missing schemas does nothing."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "absent"}
    )

    assert result["changed"] is False
    assert result["exists"] is False
    assert result["executed_queries"] == []


def test_ensure_schema_check_mode_predicts_create_without_writing() -> None:
    """Verify check mode predicts creation."""
    connection = FakeConnection()

    result = exasol_schema.ensure_schema(
        connection, {"name": "SALES", "state": "present"}, check_mode=True
    )

    assert result["changed"] is True
    assert result["exists"] is True

    assert result["executed_queries"] == ['CREATE SCHEMA "SALES"']

    assert connection.schemas == set()


def test_ensure_schema_check_mode_predicts_drop_without_writing() -> None:
    """Verify check mode predicts dropping."""
    connection = FakeConnection(schemas={"SALES"})

    result = exasol_schema.ensure_schema(
        connection,
        {"name": "SALES", "state": "absent", "cascade": True},
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["exists"] is False

    assert result["executed_queries"] == ['DROP SCHEMA "SALES" CASCADE']

    assert connection.schemas == {"SALES"}


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"name": "", "state": "present"}, "name must be a non-empty string"),
        ({"name": "SALES", "state": "invalid"}, "state must be one of"),
        ({"name": "SALES\x00"}, "must not contain NUL characters"),
        ({"name": '"unterminated'}, "malformed delimited identifier syntax"),
    ],
)
def test_ensure_schema_rejects_invalid_parameters(
    params: dict[str, object], message: str
) -> None:
    """Verify invalid schema lifecycle parameters fail."""
    connection = FakeConnection()

    with pytest.raises(ValueError, match=message):
        exasol_schema.ensure_schema(connection, params)


def test_schema_metadata_rejects_unexpected_row_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify metadata probing rejects unexpected query results."""

    def execute_queries(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"query_result": [("SALES",)]}

    monkeypatch.setattr(exasol_schema.common_query, "execute_queries", execute_queries)

    with pytest.raises(ValueError, match="unexpected row"):
        exasol_schema._schema_metadata(object(), "SALES")


def test_normalized_error_message_delegates_schema_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify normalized errors delegate correctly."""

    def normalized_exasol_error_message(
        error: BaseException, *, params: dict[str, object], operation: str
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
            params={"name": "SALES"},
            operation="schema operation",
        )
        == "schema operation failed"
    )


def test_sanitize_error_message_redacts_password() -> None:
    """Verify schema errors sanitize sensitive connection values."""
    message = exasol_schema.sanitize_error_message(
        RuntimeError("failed near SALES password123"), {"login_password": "password123"}
    )

    assert message == "failed near SALES ********"


def test_run_schema_uses_shared_connection_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify schema execution is routed through the runtime connection helper."""
    connection = object()
    params = {"name": "SALES"}

    class _ConnectionContext:
        def __enter__(self) -> object:
            return connection

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    monkeypatch.setattr(
        exasol_schema.common_query,
        "connect_to_exasol",
        lambda passed_params, module_name: _ConnectionContext(),
    )
    monkeypatch.setattr(
        exasol_schema,
        "ensure_schema",
        lambda passed_connection, passed_params, check_mode=False: {
            "connection": passed_connection,
            "params": passed_params,
            "check_mode": check_mode,
        },
    )

    assert exasol_schema.run_schema(params, check_mode=True) == {
        "connection": connection,
        "params": params,
        "check_mode": True,
    }


@pytest.mark.parametrize(
    "identifier", [object(), "", '"unterminated', '"bad"quote"', f"A{'B' * 128}"]
)
def test_validate_schema_name_rejects_invalid_identifiers(identifier: object) -> None:
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


def _quoted_identifiers(query: str) -> list[str]:
    """Extract simple quoted identifiers used by the fake connection."""
    values: list[str] = []
    remaining = query
    while '"' in remaining:
        start = remaining.index('"')
        end = remaining.index('"', start + 1)
        values.append(remaining[start + 1 : end])
        remaining = remaining[end + 1 :]
    return values


def _move_metadata(values: dict[str, Any], old_name: str, new_name: str) -> None:
    if old_name in values:
        values[new_name] = values.pop(old_name)


def _sql_comment(query: str) -> str | None:
    value = query.split(" IS ", 1)[1]
    if value == "NULL":
        return None
    return value[1:-1].replace("''", "'")


def _matching_identifier(values: set[str], identifier: str) -> str | None:
    """Find identifier using Exasol case-insensitive comparison."""
    for value in values:
        if value.casefold() == identifier.casefold():
            return value

    return None
