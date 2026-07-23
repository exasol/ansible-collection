"""Pure Python backend integration tests for the grants runtime."""

from __future__ import annotations

import pytest
from ansible_modules.common_helpers import (
    execute_sql,
    row_int,
    unique_name,
)

from exasol.ansible_modules import (
    exasol_grants,
    exasol_query,
    exasol_user,
)
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier,
    quote_identifier,
)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-missing-system-privilege")
def test_grants_runtime_grants_missing_system_privilege(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the grants runtime grants a missing system privilege."""
    user_name = _create_user_without_create_session(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION"],
        }
    )

    assert result == {
        "changed": True,
        "principal": user_name,
        "principal_type": "user",
        "state": "present",
        "executed_queries": [_grant_system_query("CREATE SESSION", user_name)],
    }
    assert (
        _system_privilege_count(
            exasol_login_vars, grantee=user_name, privilege="CREATE SESSION"
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-system-privilege-idempotent")
# [itest -> dsn~authorization-state-reconciliation~1]
# [itest -> dsn~plan-authorization-lifecycle-sql-from-metadata~1]
# [itest -> dsn~derive-changed-from-planned-sql~1]
def test_grants_runtime_existing_system_privilege_is_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify an existing system privilege is unchanged."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    execute_sql(exasol_login_vars, _grant_system_query("CREATE SESSION", user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION"],
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []
    assert (
        _system_privilege_count(
            exasol_login_vars, grantee=user_name, privilege="CREATE SESSION"
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-multiple-system-and-object-privileges")
def test_grants_runtime_grants_multiple_system_and_object_privileges(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify mixed system and object privilege requests."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(
        exasol_login_vars,
        f"CREATE SCHEMA {quote_identifier(schema_name)}",
    )
    execute_sql(
        exasol_login_vars,
        f"CREATE TABLE {quote_identifier(schema_name)}.FACT_SALES (ID DECIMAL(18,0))",
    )

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION", "CREATE SCHEMA"],
            "object_privileges": [
                {"schema": schema_name, "privileges": ["USAGE"]},
                {
                    "schema": schema_name,
                    "object": "FACT_SALES",
                    "privileges": ["SELECT", "INSERT"],
                },
            ],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_system_query("CREATE SESSION", user_name),
        _grant_system_query("CREATE SCHEMA", user_name),
        _grant_schema_query("USAGE", schema_name, user_name),
        _grant_object_query("SELECT", schema_name, "FACT_SALES", user_name),
        _grant_object_query("INSERT", schema_name, "FACT_SALES", user_name),
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars, grantee=user_name, privilege="CREATE SESSION"
        )
        == 1
    )
    assert (
        _schema_object_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            schema_name=schema_name,
            privilege="USAGE",
        )
        == 1
    )
    assert (
        _object_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            schema_name=schema_name,
            object_name="FACT_SALES",
            privilege="SELECT",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-revoke-existing-schema-object-privilege")
def test_grants_runtime_revokes_existing_schema_object_privilege(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify an existing schema-level object privilege is revoked."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f"CREATE SCHEMA {quote_identifier(schema_name)}")
    execute_sql(exasol_login_vars, _grant_schema_query("USAGE", schema_name, user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "state": "absent",
            "object_privileges": [{"schema": schema_name, "privileges": ["USAGE"]}],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _revoke_schema_query("USAGE", schema_name, user_name)
    ]
    assert (
        _schema_object_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            schema_name=schema_name,
            privilege="USAGE",
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-absent-schema-object-privilege-idempotent")
def test_grants_runtime_missing_schema_object_privilege_absent_is_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a missing schema-level object privilege stays unchanged."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f"CREATE SCHEMA {quote_identifier(schema_name)}")

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "state": "absent",
            "object_privileges": [{"schema": schema_name, "privileges": ["USAGE"]}],
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-check-mode-predicts-system-grant")
# [itest -> dsn~keep-check-mode-planning-deterministic-and-side-effect-free~1]
def test_grants_runtime_check_mode_predicts_system_grant(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode predicts a system grant without writing it."""
    user_name = _create_user_without_create_session(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION"],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_system_query("CREATE SESSION", user_name)
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars, grantee=user_name, privilege="CREATE SESSION"
        )
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-reject-mutually-exclusive-principals")
def test_grants_runtime_rejects_mutually_exclusive_principals(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify supplying both principal options fails validation."""
    with pytest.raises(ValueError, match="exactly one"):
        exasol_grants.run_grants(
            {
                **exasol_login_vars,
                "user": "ALICE",
                "role": "APP_ROLE",
                "system_privileges": ["CREATE SESSION"],
            }
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-role-membership-to-user")
def test_grants_runtime_grants_role_membership_to_user(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the roles option grants role membership to a user."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    role_name = _create_role(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [role_name],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [_grant_role_query(role_name, user_name)]
    assert (
        _role_grant_count(exasol_login_vars, grantee=user_name, role_name=role_name)
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-role-membership-idempotent")
def test_grants_runtime_existing_role_membership_is_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify an existing role membership is unchanged."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    role_name = _create_role(exasol_login_vars)
    execute_sql(exasol_login_vars, _grant_role_query(role_name, user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [role_name],
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-revoke-role-membership")
def test_grants_runtime_revokes_role_membership(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify an existing role membership is revoked."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    role_name = _create_role(exasol_login_vars)
    execute_sql(exasol_login_vars, _grant_role_query(role_name, user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [role_name],
            "state": "absent",
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [_revoke_role_query(role_name, user_name)]
    assert (
        _role_grant_count(exasol_login_vars, grantee=user_name, role_name=role_name)
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-check-mode-role-membership")
def test_grants_runtime_check_mode_predicts_role_membership(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode predicts a role membership grant without writing it."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    role_name = _create_role(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [role_name],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [_grant_role_query(role_name, user_name)]
    assert (
        _role_grant_count(exasol_login_vars, grantee=user_name, role_name=role_name)
        == 0
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-missing-system-privilege-to-role")
def test_grants_runtime_grants_missing_system_privilege_to_role(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify a role principal can receive a system privilege."""
    role_name = _create_role(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "role": role_name,
            "system_privileges": ["CREATE SESSION"],
        }
    )

    assert result["changed"] is True
    assert result["principal"] == role_name
    assert result["principal_type"] == "role"
    assert result["executed_queries"] == [
        _grant_system_query("CREATE SESSION", role_name)
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars, grantee=role_name, privilege="CREATE SESSION"
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-script-execute-privilege")
def test_grants_runtime_grants_script_execute_privilege(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify object_type=script renders a SCRIPT object target."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f"CREATE SCHEMA {quote_identifier(schema_name)}")
    execute_sql(
        exasol_login_vars,
        f"""
        CREATE LUA SCALAR SCRIPT {quote_identifier(schema_name)}.CALC_TOTAL()
        RETURNS DOUBLE AS
        function run(ctx)
            return 0
        end
        /
        """,
    )

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "object_privileges": [
                {
                    "schema": schema_name,
                    "object": "CALC_TOTAL",
                    "object_type": "script",
                    "privileges": ["EXECUTE"],
                }
            ],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_object_query(
            "EXECUTE", schema_name, "CALC_TOTAL", user_name, object_type="SCRIPT"
        )
    ]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-view-select-privilege")
def test_grants_runtime_grants_view_select_privilege(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify object_type=view renders a VIEW object target."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f"CREATE SCHEMA {quote_identifier(schema_name)}")
    execute_sql(
        exasol_login_vars,
        f"CREATE TABLE {quote_identifier(schema_name)}.SALES (ID DECIMAL(18,0))",
    )
    execute_sql(
        exasol_login_vars,
        (
            f"CREATE VIEW {quote_identifier(schema_name)}.SALES_VIEW AS "
            f"SELECT ID FROM {quote_identifier(schema_name)}.SALES"
        ),
    )

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "object_privileges": [
                {
                    "schema": schema_name,
                    "object": "SALES_VIEW",
                    "object_type": "view",
                    "privileges": ["SELECT"],
                }
            ],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_object_query(
            "SELECT", schema_name, "SALES_VIEW", user_name, object_type="VIEW"
        )
    ]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-check-mode-predicts-no-action-when-granted")
def test_grants_runtime_check_mode_predicts_no_action_when_granted(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode reports no action for an existing grant."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    execute_sql(exasol_login_vars, _grant_system_query("CREATE SESSION", user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION"],
        },
        check_mode=True,
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-check-mode-predicts-revoke")
def test_grants_runtime_check_mode_predicts_revoke(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify check mode predicts a revoke without executing it."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    schema_name = unique_name("ANSIBLE_PYTHON_SCHEMA")
    execute_sql(exasol_login_vars, f"CREATE SCHEMA {quote_identifier(schema_name)}")
    execute_sql(exasol_login_vars, _grant_schema_query("USAGE", schema_name, user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "state": "absent",
            "object_privileges": [{"schema": schema_name, "privileges": ["USAGE"]}],
        },
        check_mode=True,
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _revoke_schema_query("USAGE", schema_name, user_name)
    ]
    assert (
        _schema_object_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            schema_name=schema_name,
            privilege="USAGE",
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-grants-grant-batch-with-some-privileges-already-present"
)
def test_grants_runtime_grants_batch_with_some_privileges_already_present(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify mixed-batch idempotency grants only missing privileges."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    execute_sql(exasol_login_vars, _grant_system_query("CREATE SESSION", user_name))

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SESSION", "CREATE SCHEMA"],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_system_query("CREATE SCHEMA", user_name)
    ]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-absent-system-privilege-idempotent")
def test_grants_runtime_missing_system_privilege_absent_is_unchanged(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify absent state is idempotent for missing system privileges."""
    user_name = _create_user_without_create_session(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["CREATE SCHEMA"],
            "state": "absent",
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-reject-unsupported-privilege")
def test_grants_runtime_rejects_unsupported_privilege(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify unsupported privileges fail validation."""
    with pytest.raises(ValueError, match="unsupported Exasol system privilege"):
        exasol_grants.run_grants(
            {
                **exasol_login_vars,
                "user": "ALICE",
                "system_privileges": ["DROP DATABASE"],
            }
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-reject-empty-request")
def test_grants_runtime_rejects_empty_request(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify requests without grant targets fail validation."""
    with pytest.raises(ValueError, match="at least one"):
        exasol_grants.run_grants({**exasol_login_vars, "user": "ALICE"})


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-preserves-exact-identifier")
def test_grants_runtime_preserves_exact_identifier(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify exact role identifiers are preserved in generated SQL."""
    role_name = _create_role(
        exasol_login_vars,
        name=unique_name("ANSIBLE_ROLE_EXACT+/=Role"),
    )

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "role": f'"{role_name}"',
            "system_privileges": ["CREATE SESSION"],
        }
    )

    assert result["changed"] is True
    assert result["principal"] == role_name
    assert result["executed_queries"] == [
        _grant_system_query("CREATE SESSION", role_name)
    ]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-idempotent-with-different-case-spelling")
def test_grants_runtime_idempotent_with_different_case_spelling(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify case-only spelling differences are idempotent."""
    role_name = _create_role(
        exasol_login_vars,
        name=unique_name("ANSIBLE_ROLE_EXACT+/=Role"),
    )
    execute_sql(exasol_login_vars, _grant_system_query("CREATE SESSION", role_name))
    lower_case_role_name = role_name.lower()

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "role": f'"{lower_case_role_name}"',
            "system_privileges": ["CREATE SESSION"],
        }
    )

    assert result["changed"] is False
    assert result["executed_queries"] == []


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-system-privilege-with-admin-option")
def test_grants_runtime_grants_system_privilege_with_admin_option(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify admin_option grants system privileges with admin option."""
    user_name = _create_user_without_create_session(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["SELECT ANY TABLE"],
            "admin_option": True,
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_system_query("SELECT ANY TABLE", user_name, admin_option=True)
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            privilege="SELECT ANY TABLE",
            admin_option=True,
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-grants-grant-mixed-system-privileges-with-admin-options"
)
def test_grants_runtime_grants_mixed_system_privileges_with_admin_options(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify system privilege entries can carry admin option values."""
    user_name = _create_user_without_create_session(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": [
                {"privilege": "SELECT ANY TABLE", "admin_option": True},
                {"privilege": "CREATE SESSION", "admin_option": False},
            ],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_system_query("SELECT ANY TABLE", user_name, admin_option=True),
        _grant_system_query("CREATE SESSION", user_name),
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            privilege="SELECT ANY TABLE",
            admin_option=True,
        )
        == 1
    )
    assert (
        _system_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            privilege="CREATE SESSION",
            admin_option=False,
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-grant-role-membership-with-admin-option")
def test_grants_runtime_grants_role_membership_with_admin_option(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify admin_option grants role memberships with admin option."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    role_name = _create_role(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [role_name],
            "admin_option": True,
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_role_query(role_name, user_name, admin_option=True)
    ]
    assert (
        _role_grant_count(
            exasol_login_vars,
            grantee=user_name,
            role_name=role_name,
            admin_option=True,
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id(
    "exasol-grants-grant-mixed-role-memberships-with-admin-options"
)
def test_grants_runtime_grants_mixed_role_memberships_with_admin_options(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify role entries can carry per-role admin option values."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    reader_role = _create_role(exasol_login_vars)
    writer_role = _create_role(exasol_login_vars)

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "roles": [
                {"role": reader_role, "admin_option": True},
                {"role": writer_role, "admin_option": False},
            ],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _grant_role_query(reader_role, user_name, admin_option=True),
        _grant_role_query(writer_role, user_name),
    ]
    assert (
        _role_grant_count(
            exasol_login_vars,
            grantee=user_name,
            role_name=reader_role,
            admin_option=True,
        )
        == 1
    )
    assert (
        _role_grant_count(
            exasol_login_vars,
            grantee=user_name,
            role_name=writer_role,
            admin_option=False,
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-downgrade-system-privilege-admin-option")
def test_grants_runtime_downgrades_system_privilege_admin_option(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify admin_option=false re-grants system privileges without admin."""
    user_name = _create_user_without_create_session(exasol_login_vars)
    execute_sql(
        exasol_login_vars,
        _grant_system_query("SELECT ANY TABLE", user_name, admin_option=True),
    )

    result = exasol_grants.run_grants(
        {
            **exasol_login_vars,
            "user": user_name,
            "system_privileges": ["SELECT ANY TABLE"],
        }
    )

    assert result["changed"] is True
    assert result["executed_queries"] == [
        _revoke_system_query("SELECT ANY TABLE", user_name),
        _grant_system_query("SELECT ANY TABLE", user_name),
    ]
    assert (
        _system_privilege_count(
            exasol_login_vars,
            grantee=user_name,
            privilege="SELECT ANY TABLE",
            admin_option=False,
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.scenario_id("exasol-grants-reject-admin-option-for-object-only-request")
def test_grants_runtime_rejects_admin_option_for_object_only_request(
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify admin_option is rejected when no applicable grants are requested."""
    with pytest.raises(ValueError, match="admin_option applies only"):
        exasol_grants.run_grants(
            {
                **exasol_login_vars,
                "user": "ALICE",
                "object_privileges": [
                    {"schema": "APP_SCHEMA", "privileges": ["USAGE"]}
                ],
                "admin_option": True,
            }
        )


def _create_user_without_create_session(login_vars: dict[str, object]) -> str:
    user_name = unique_name("ANSIBLE_PYTHON_USER")
    exasol_user.run_user(
        {
            **login_vars,
            "name": user_name,
            "password": "Exasol123",
            "create_session": False,
        }
    )
    return user_name


def _create_role(login_vars: dict[str, object], name: str | None = None) -> str:
    role_name = name or unique_name("ANSIBLE_PYTHON_ROLE")
    execute_sql(login_vars, f"CREATE ROLE {quote_exact_identifier(role_name)}")
    return role_name


def _grant_system_query(
    privilege: str,
    principal: str,
    *,
    admin_option: bool = False,
) -> str:
    return _with_admin_option(
        f"GRANT {privilege} TO {quote_exact_identifier(principal)}",
        admin_option,
    )


def _revoke_system_query(privilege: str, principal: str) -> str:
    return f"REVOKE {privilege} FROM {quote_exact_identifier(principal)}"


def _grant_schema_query(privilege: str, schema_name: str, principal: str) -> str:
    return (
        f"GRANT {privilege} ON {quote_identifier(schema_name)} "
        f"TO {quote_exact_identifier(principal)}"
    )


def _grant_object_query(
    privilege: str,
    schema_name: str,
    object_name: str,
    principal: str,
    *,
    object_type: str | None = None,
) -> str:
    target = f"{quote_identifier(schema_name)}.{quote_identifier(object_name)}"
    if object_type is not None:
        target = f"{object_type} {target}"

    return f"GRANT {privilege} ON {target} " f"TO {quote_exact_identifier(principal)}"


def _revoke_schema_query(privilege: str, schema_name: str, principal: str) -> str:
    return (
        f"REVOKE {privilege} ON {quote_identifier(schema_name)} "
        f"FROM {quote_exact_identifier(principal)}"
    )


def _grant_role_query(
    role_name: str,
    principal: str,
    *,
    admin_option: bool = False,
) -> str:
    return _with_admin_option(
        (
            f"GRANT {quote_exact_identifier(role_name)} "
            f"TO {quote_exact_identifier(principal)}"
        ),
        admin_option,
    )


def _revoke_role_query(role_name: str, principal: str) -> str:
    return (
        f"REVOKE {quote_exact_identifier(role_name)} "
        f"FROM {quote_exact_identifier(principal)}"
    )


def _system_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    privilege: str,
    admin_option: bool | None = None,
) -> int:
    admin_filter = _admin_option_filter(admin_option)
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_SYS_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        {admin_filter}
        """,
    )


def _schema_object_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    schema_name: str,
    privilege: str,
) -> int:
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_OBJ_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        AND UPPER(COALESCE(OBJECT_SCHEMA, OBJECT_NAME)) =
            UPPER({_quote_sql_literal(schema_name)})
        AND (OBJECT_NAME IS NULL OR UPPER(OBJECT_NAME) =
            UPPER({_quote_sql_literal(schema_name)}))
        """,
    )


def _object_privilege_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    schema_name: str,
    object_name: str,
    privilege: str,
) -> int:
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_OBJ_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND PRIVILEGE = {_quote_sql_literal(privilege)}
        AND UPPER(OBJECT_SCHEMA) = UPPER({_quote_sql_literal(schema_name)})
        AND UPPER(OBJECT_NAME) = UPPER({_quote_sql_literal(object_name)})
        """,
    )


def _role_grant_count(
    login_vars: dict[str, object],
    *,
    grantee: str,
    role_name: str,
    admin_option: bool | None = None,
) -> int:
    admin_filter = _admin_option_filter(admin_option)
    return _metadata_count(
        login_vars,
        f"""
        SELECT COUNT(*) AS PRIVILEGE_COUNT
        FROM EXA_DBA_ROLE_PRIVS
        WHERE UPPER(GRANTEE) = UPPER({_quote_sql_literal(grantee)})
        AND UPPER(GRANTED_ROLE) = UPPER({_quote_sql_literal(role_name)})
        {admin_filter}
        """,
    )


def _metadata_count(login_vars: dict[str, object], query: str) -> int:
    with exasol_query.connect_to_exasol(
        login_vars,
        module_name="python package integration test",
    ) as connection:
        rows = connection.execute(query).fetchall()

    return row_int(rows[0], "PRIVILEGE_COUNT")


def _quote_sql_literal(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _with_admin_option(query: str, admin_option: bool) -> str:
    if not admin_option:
        return query

    return f"{query} WITH ADMIN OPTION"


def _admin_option_filter(admin_option: bool | None) -> str:
    if admin_option is None:
        return ""

    return f"AND ADMIN_OPTION = {str(admin_option).upper()}"
