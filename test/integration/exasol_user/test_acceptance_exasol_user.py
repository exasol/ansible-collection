"""Playbook-backed tests for exasol-user feature scenarios."""

from __future__ import annotations

import os
from typing import Any

import pytest

from ..acceptance_common.acceptance_test_common import (
    given_acceptance_context,
    then_result_matches,
    then_secret_is_not_exposed,
    when_module_scenario_runs,
)

MODULE_NAME = "exasol_user"


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_create_missing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Create missing user."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-create-missing-user",
    )

    then_result_matches(
        _without_result_json(result),
        {
            "changed": True,
            "exists": True,
            "user": context.test_user,
            "login_value": "17",
            "executed_query_count": "2",
            "user_count": "1",
        },
    )
    then_secret_is_not_exposed(result, context.test_user_password)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_apply_unchanged(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Applying identical user state results in no changes."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-apply-unchanged",
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "exists": True,
            "executed_query_count": 0,
        },
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_change_authentication_to_ldap(
    request: pytest.FixtureRequest,
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Change authentication to LDAP."""
    if not _backend_supports_ldap(request):
        pytest.skip("Exasol SaaS does not support LDAP-authenticated database users")

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-change-authentication-to-ldap",
    )

    then_result_matches(
        _without_result_json(result),
        {
            "changed": True,
            "exists": True,
            "ldap_dn": context.test_user_ldap_dn,
        },
    )
    then_secret_is_not_exposed(result, context.test_user_ldap_dn)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_rotate_password(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Rotate password."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-rotate-password",
    )

    then_result_matches(
        _without_result_json(result),
        {
            "changed": True,
            "exists": True,
            "login_value": "19",
        },
    )
    then_secret_is_not_exposed(result, context.test_user_rotated_password)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_check_mode_create(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts create."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-check-mode-create",
    )

    then_result_matches(
        _without_result_json(result),
        {
            "changed": True,
            "predicted_exists": True,
            "user_count": "0",
        },
    )
    then_secret_is_not_exposed(result, context.check_mode_user_password)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_check_mode_update_ldap(
    request: pytest.FixtureRequest,
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts LDAP update."""
    if _backend_is_saas(request):
        pytest.skip("Exasol SaaS does not support LDAP-authenticated database users")

    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-check-mode-update-ldap",
    )

    then_result_matches(
        _without_result_json(result),
        {
            "changed": True,
            "exists": True,
            "ldap_dn": "",
        },
    )
    then_secret_is_not_exposed(result, context.check_mode_user_ldap_dn)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_check_mode_drop(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Check mode predicts drop."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-check-mode-drop",
    )

    then_result_matches(
        result,
        {
            "changed": True,
            "predicted_exists": False,
            "user_count": "1",
        },
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_drop_existing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Drop existing user."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-drop-existing-user",
    )

    then_result_matches(
        result,
        {
            "changed": True,
            "exists": False,
            "user_count": "0",
        },
    )


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_user_drop_missing_user(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Scenario: Drop missing user."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)

    result = when_module_scenario_runs(
        context,
        MODULE_NAME,
        "exasol-user-drop-missing-user",
    )

    then_result_matches(
        result,
        {
            "changed": False,
            "exists": False,
            "executed_query_count": 0,
        },
    )


def _without_result_json(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "result_json"}


def _backend_supports_ldap(request: pytest.FixtureRequest) -> bool:
    if _backend_is_saas(request):
        return False

    return os.environ.get("EXASOL_BACKEND_SUPPORTS_LDAP", "").lower() in {
        "1",
        "true",
        "yes",
    }


def _backend_is_saas(request: pytest.FixtureRequest) -> bool:
    callspec = getattr(request.node, "callspec", None)

    return getattr(callspec, "id", "") == "saas"
