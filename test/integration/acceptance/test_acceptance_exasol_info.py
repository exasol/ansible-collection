"""Playbook-backed tests for exasol-info feature scenarios."""

from __future__ import annotations

import re
from test.integration.acceptance_common.acceptance_test_common import (
    given_acceptance_context,
    when_module_scenario_runs,
)
from typing import Any

import pytest

MODULE_NAME = "exasol_info"
SEMVER_LIKE_VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9._-]+)?$")


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_info_return_cluster_info(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Returns version and cluster info."""
    scenario_id = "exasol-info-return-cluster-info"
    playbook = """
    - name: Return version and cluster info
      block:
        - name: When exasol_info runs with valid credentials
          exasol.exasol.exasol_info:
          register: exasol_info_result

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              module_result: "{{ exasol_info_result }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    module_result = result["module_result"]

    assert module_result["changed"] is False
    assert isinstance(module_result["version"], str)
    assert SEMVER_LIKE_VERSION.match(module_result["version"])
    assert isinstance(module_result["database_name"], str)
    assert module_result["database_name"]
    assert isinstance(module_result["cluster_size"], int)
    assert module_result["cluster_size"] >= 1


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_info_check_mode(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode returns the same info payload."""
    scenario_id = "exasol-info-check-mode"
    playbook = """
    - name: Supports check mode
      block:
        - name: When exasol_info runs with valid credentials
          exasol.exasol.exasol_info:
          register: exasol_info_normal_result

        - name: When exasol_info runs in check mode with valid credentials
          exasol.exasol.exasol_info:
          check_mode: true
          register: exasol_info_check_mode_result

        - name: Store scenario result
          ansible.builtin.set_fact:
            acceptance_result:
              scenario_id: "{{ acceptance_scenario_id }}"
              normal_result: "{{ exasol_info_normal_result }}"
              check_mode_result: "{{ exasol_info_check_mode_result }}"
            cacheable: true
    """

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        scenario_id,
        scenario_playbook=playbook,
    )

    normal_result = result["normal_result"]
    check_mode_result = result["check_mode_result"]

    assert check_mode_result["changed"] is False
    assert check_mode_result["version"] == normal_result["version"]
    assert check_mode_result["database_name"] == normal_result["database_name"]
    assert check_mode_result["cluster_size"] == normal_result["cluster_size"]
