"""Tests for the shared integration-test recording connection."""

from __future__ import annotations

from typing import Any

from common.recording_connection import RecordingConnection


class FakeConnection:
    """Record execution calls and return a stable result."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self.result = object()

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> object:
        self.calls.append((query, query_params))
        return self.result


def test_recording_connection_normalizes_and_delegates_query() -> None:
    """Verify the wrapper records normalized SQL and preserves its execution call."""
    connection = FakeConnection()
    recording_connection = RecordingConnection(connection)
    query = "SELECT  PARAM_VALUE\nFROM SYS.EXA_METADATA"
    query_params = {"parameter_name": "databaseName"}

    result = recording_connection.execute(query, query_params)

    assert result is connection.result
    assert recording_connection.queries == ["SELECT PARAM_VALUE FROM SYS.EXA_METADATA"]
    assert connection.calls == [(query, query_params)]
