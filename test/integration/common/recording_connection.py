"""Connection wrapper that records normalized SQL for integration tests."""

from __future__ import annotations

from typing import (
    Any,
    Protocol,
)


class ExecutableConnection(Protocol):
    """Minimal connection contract required by the recording wrapper."""

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> object:
        """Execute one SQL query."""


class RecordingConnection:
    """Record SQL while delegating execution to a real Exasol connection."""

    def __init__(self, connection: ExecutableConnection) -> None:
        self._connection = connection
        self.queries: list[str] = []

    def execute(
        self,
        query: str,
        query_params: dict[str, Any] | None = None,
    ) -> object:
        self.queries.append(" ".join(query.split()))
        return self._connection.execute(query, query_params)
