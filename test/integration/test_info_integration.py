"""Pure Python backend integration tests for the info runtime."""

from __future__ import annotations

import pytest

from exasol.ansible_modules import exasol_info


@pytest.mark.integration
@pytest.mark.slow
def test_info_runtime_reads_basic_server_metadata(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the info runtime gathers a stable metadata payload."""
    result = exasol_info.run_info(exasol_login_vars)

    expected_result = {
        "changed": False,
        "database_name": "DB1",
        "cluster_size": 1,
    }
    assert {key: result[key] for key in expected_result} == expected_result
    assert isinstance(result["version"], str)
    assert result["version"] != ""


@pytest.mark.integration
@pytest.mark.slow
def test_info_runtime_check_mode_stays_read_only(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode does not alter the runtime metadata payload."""
    normal_result = exasol_info.run_info(exasol_login_vars)
    check_mode_result = exasol_info.run_info(exasol_login_vars, check_mode=True)

    assert check_mode_result == normal_result
