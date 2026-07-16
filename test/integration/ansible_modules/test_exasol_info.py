"""Pure Python backend integration tests for the info runtime."""

from __future__ import annotations

import pytest

from exasol.ansible_modules import exasol_info


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
