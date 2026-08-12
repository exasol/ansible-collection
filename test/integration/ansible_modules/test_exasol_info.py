"""Pure Python backend integration tests for the info runtime."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import cast

import pytest
from common.recording_connection import (
    ExecutableConnection,
    RecordingConnection,
)

from exasol.ansible_modules import (
    common_query,
    exasol_info,
)


class ConnectionContext(AbstractContextManager[object]):
    """Provide one already-open connection through the shared helper contract."""

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def __enter__(self) -> object:
        return self._connection

    def __exit__(self, *args: object) -> None:
        return None


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-info-returns-version-and-cluster-size")
def test_info_runtime_reads_basic_server_metadata(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the info runtime gathers a stable metadata payload."""
    result = exasol_info.run_info(exasol_login_vars)

    assert result["changed"] is False
    assert isinstance(result["version"], str)
    assert result["version"] != ""
    assert isinstance(result["database_name"], str)
    assert result["database_name"] != ""
    assert isinstance(result["cluster_size"], int)
    assert result["cluster_size"] >= 1

    expected_result = {
        "changed": False,
        "database_name": "DB1",
        "cluster_size": 1,
    }
    assert {key: result[key] for key in expected_result} == expected_result


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-info-uses-qualified-statistical-cluster-metadata-view")
# [itest -> dsn~exasol-info-read-only-metadata-retrieval~3]
def test_info_runtime_uses_qualified_statistical_cluster_metadata_view(
    exasol_login_vars: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the real runtime sends the qualified statistical cluster query."""
    with common_query.connect_to_exasol(
        exasol_login_vars,
        module_name="info metadata acceptance test",
    ) as connection:
        recording_connection = RecordingConnection(
            cast(ExecutableConnection, connection)
        )
        monkeypatch.setattr(
            exasol_info.common_query,
            "connect_to_exasol",
            lambda *_args, **_kwargs: ConnectionContext(recording_connection),
        )

        result = exasol_info.run_info(exasol_login_vars)

    assert result["version"]
    assert recording_connection.queries[-1] == (
        "SELECT NODES AS CLUSTER_SIZE FROM EXA_STATISTICS.EXA_SYSTEM_EVENTS"
    )
