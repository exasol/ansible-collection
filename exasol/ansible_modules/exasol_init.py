"""Orchestrate Exasol environment initialization (roles, users, role grants,
schemas, schema privilege grants, and init scripts) as one Ansible module.

The phase order below implements the dependency analysis in
specs/glossary/exasol_init_glossary.md and
specs/diagrams/exasol_init_process_diagram.md:

* Roles and Users are independent (created in a fixed order only for
  deterministic output, not because of a real dependency).
* Role Assignments need both a Role and a User.
* Schemas are independent unless an owner is requested, in which case that
  owner User must already exist.
* Schema Privilege Grants need the grantee (Role or User) and the Schema.
* Init Scripts run last, after the schema exists and every requested grant
  has been applied.

A run executes in two passes so present/absent items can be mixed in one
call: a teardown pass (reverse dependency order) followed by a
reconciliation pass (forward dependency order). See "Initialization Run" in
the glossary.
"""

from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from typing import cast

from exasol.ansible_modules import (
    common_query,
    common_role,
    common_schema,
    common_user,
    exasol_query,
)
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    validate_exact_identifier,
    validate_role_name,
    validate_schema_name,
    validate_user_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

DEFAULT_STATE = "present"
STATES = frozenset({"present", "absent"})
PRIVILEGES = frozenset(
    {
        "ALL",
        "ALTER",
        "DELETE",
        "EXECUTE",
        "INDEX",
        "INSERT",
        "REFERENCES",
        "SELECT",
        "UPDATE",
    }
)

ROLE_GRANT_QUERY = """
SELECT GRANTEE, GRANTED_ROLE
FROM EXA_DBA_ROLE_GRANTS
WHERE UPPER(GRANTEE) = UPPER(:grantee) AND UPPER(GRANTED_ROLE) = UPPER(:role)
"""

SCHEMA_GRANT_QUERY = """
SELECT OBJECT_NAME, GRANTEE, PRIVILEGE
FROM EXA_DBA_OBJ_PRIVS
WHERE UPPER(OBJECT_NAME) = UPPER(:schema_name)
  AND UPPER(GRANTEE) = UPPER(:grantee)
  AND UPPER(PRIVILEGE) = UPPER(:privilege)
"""


# -----------------------------
# Public API
# -----------------------------


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for exasol_init."""
    return {
        **common_query.exasol_connection_argument_spec(),
        "roles": {
            "type": "list",
            "elements": "dict",
            "default": [],
            "options": {
                "name": {"type": "str", "required": True},
                "state": {
                    "type": "str",
                    "choices": sorted(STATES),
                    "default": DEFAULT_STATE,
                },
                "cascade": {"type": "bool", "default": False},
            },
        },
        "users": {
            "type": "list",
            "elements": "dict",
            "default": [],
            "options": {
                "name": {"type": "str", "required": True},
                "password": {"type": "str", "no_log": True},
                "authentication_method": {
                    "type": "str",
                    "choices": sorted(common_user.AUTHENTICATION_METHODS),
                },
                "ldap_dn": {"type": "str", "no_log": True},
                "state": {
                    "type": "str",
                    "choices": sorted(STATES),
                    "default": DEFAULT_STATE,
                },
                "update_password": {
                    "type": "str",
                    "choices": sorted(common_user.UPDATE_MODES),
                    "default": common_user.DEFAULT_UPDATE_MODE,
                    "no_log": False,
                },
                "create_session": {"type": "bool", "default": True},
                "cascade": {"type": "bool", "default": False},
            },
        },
        "role_grants": {
            "type": "list",
            "elements": "dict",
            "default": [],
            "options": {
                "role": {"type": "str", "required": True},
                "user": {"type": "str", "required": True},
                "state": {
                    "type": "str",
                    "choices": sorted(STATES),
                    "default": DEFAULT_STATE,
                },
            },
        },
        "schemas": {
            "type": "list",
            "elements": "dict",
            "default": [],
            "options": {
                "name": {"type": "str", "required": True},
                "owner": {"type": "str"},
                "state": {
                    "type": "str",
                    "choices": sorted(STATES),
                    "default": DEFAULT_STATE,
                },
                "cascade": {"type": "bool", "default": False},
            },
        },
        "grants": {
            "type": "list",
            "elements": "dict",
            "default": [],
            "options": {
                "schema": {"type": "str", "required": True},
                "privilege": {
                    "type": "str",
                    "required": True,
                    "choices": sorted(PRIVILEGES),
                },
                "grantee": {"type": "str", "required": True},
                "state": {
                    "type": "str",
                    "choices": sorted(STATES),
                    "default": DEFAULT_STATE,
                },
            },
        },
        "scripts": {"type": "list", "elements": "str", "default": []},
    }


def run_init(
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Connect to Exasol and initialize the requested environment."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_init",
    ) as connection:
        return ensure_init(connection, params, check_mode=check_mode)


def ensure_init(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure the requested Exasol environment in dependency order."""
    roles = _items(params, "roles")
    users = _items(params, "users")
    role_grants = _items(params, "role_grants")
    schemas = _items(params, "schemas")
    grants = _items(params, "grants")
    scripts = _scripts(params)

    teardown_roles, create_roles = _split_by_state(roles)
    teardown_users, create_users = _split_by_state(users)
    teardown_role_grants, create_role_grants = _split_by_state(role_grants)
    teardown_schemas, create_schemas = _split_by_state(schemas)
    teardown_grants, create_grants = _split_by_state(grants)

    executed_queries: list[str] = []
    results: dict[str, object] = {
        "roles": [],
        "users": [],
        "role_grants": [],
        "schemas": [],
        "grants": [],
        "scripts": {"changed": False, "executed_queries": []},
    }

    # Pass 1: teardown, reverse dependency order.
    _run_phase(
        results["grants"],  # type: ignore[arg-type]
        executed_queries,
        teardown_grants,
        lambda item: _ensure_schema_grant(connection, item, check_mode),
    )
    _run_phase(
        results["role_grants"],  # type: ignore[arg-type]
        executed_queries,
        teardown_role_grants,
        lambda item: _ensure_role_grant(connection, item, check_mode),
    )
    _run_phase(
        results["schemas"],  # type: ignore[arg-type]
        executed_queries,
        teardown_schemas,
        lambda item: common_schema.ensure_schema(connection, item, check_mode),
    )
    _run_phase(
        results["users"],  # type: ignore[arg-type]
        executed_queries,
        teardown_users,
        lambda item: common_user.ensure_user(connection, item, check_mode),
    )
    _run_phase(
        results["roles"],  # type: ignore[arg-type]
        executed_queries,
        teardown_roles,
        lambda item: common_role.ensure_role(connection, item, check_mode),
    )

    # Pass 2: reconciliation, forward dependency order.
    _run_phase(
        results["roles"],  # type: ignore[arg-type]
        executed_queries,
        create_roles,
        lambda item: common_role.ensure_role(connection, item, check_mode),
    )
    _run_phase(
        results["users"],  # type: ignore[arg-type]
        executed_queries,
        create_users,
        lambda item: common_user.ensure_user(connection, item, check_mode),
    )
    _run_phase(
        results["role_grants"],  # type: ignore[arg-type]
        executed_queries,
        create_role_grants,
        lambda item: _ensure_role_grant(connection, item, check_mode),
    )
    _run_phase(
        results["schemas"],  # type: ignore[arg-type]
        executed_queries,
        create_schemas,
        lambda item: common_schema.ensure_schema(connection, item, check_mode),
    )
    _run_phase(
        results["grants"],  # type: ignore[arg-type]
        executed_queries,
        create_grants,
        lambda item: _ensure_schema_grant(connection, item, check_mode),
    )

    scripts_result = _ensure_scripts(connection, scripts, check_mode)
    results["scripts"] = scripts_result
    executed_queries.extend(cast(list[str], scripts_result["executed_queries"]))

    return {
        "changed": bool(executed_queries),
        "executed_queries": executed_queries,
        **results,
    }


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact sensitive data from an error message."""
    return common_query.sanitize_error_message(error, _params_with_secrets(params))


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol environment initialization",
) -> str:
    """Return a sanitized user-facing error message."""
    return common_query.normalized_exasol_error_message(
        error,
        params=_params_with_secrets(params),
        operation=operation,
    )


# -----------------------------
# Internal logic
# -----------------------------


def _items(params: Mapping[str, object], key: str) -> list[dict[str, object]]:
    value = params.get(key) or []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of objects.")

    items = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{key} entries must be objects.")
        items.append(dict(item))
    return items


def _scripts(params: Mapping[str, object]) -> list[str]:
    scripts = params.get("scripts") or []
    if not isinstance(scripts, Sequence) or isinstance(scripts, (str, bytes)):
        raise ValueError("scripts must be a list of SQL statements.")
    return [str(script) for script in scripts]


def _split_by_state(
    items: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    teardown = [item for item in items if item.get("state") == "absent"]
    create = [item for item in items if item.get("state") != "absent"]
    return teardown, create


def _run_phase(
    phase_results: list[dict[str, object]],
    executed_queries: list[str],
    items: list[dict[str, object]],
    ensure_item: object,
) -> None:
    for item in items:
        result = ensure_item(item)  # type: ignore[operator]
        phase_results.append(result)
        executed_queries.extend(result["executed_queries"])


def _ensure_role_grant(
    connection: object,
    item: Mapping[str, object],
    check_mode: bool,
) -> dict[str, object]:
    role_name = validate_role_name(validate_required_param(item, "role"))
    user_name = validate_user_name(validate_required_param(item, "user"))
    state = validate_choice_param(item, "state", DEFAULT_STATE, STATES)
    exists = _role_grant_exists(connection, role_name, user_name)

    if state == "absent":
        statements = (
            [] if not exists else [_revoke_role_statement(role_name, user_name)]
        )
    else:
        statements = [] if exists else [_grant_role_statement(role_name, user_name)]

    if statements and not check_mode:
        common_query.execute_queries(connection, statements)

    return {
        "changed": bool(statements),
        "role": role_name,
        "user": user_name,
        "granted": state == "present" if statements else exists,
        "executed_queries": statements,
    }


def _role_grant_exists(connection: object, role_name: str, user_name: str) -> bool:
    result = common_query.execute_queries(
        connection,
        ROLE_GRANT_QUERY,
        named_args={"role": role_name, "grantee": user_name},
    )
    return bool(result["query_result"])


def _grant_role_statement(role_name: str, user_name: str) -> str:
    quoted_role = quote_exact_identifier_value(role_name, identifier_type="role")
    quoted_user = quote_exact_identifier_value(user_name, identifier_type="user")
    return f"GRANT {quoted_role} TO {quoted_user}"


def _revoke_role_statement(role_name: str, user_name: str) -> str:
    quoted_role = quote_exact_identifier_value(role_name, identifier_type="role")
    quoted_user = quote_exact_identifier_value(user_name, identifier_type="user")
    return f"REVOKE {quoted_role} FROM {quoted_user}"


def _ensure_schema_grant(
    connection: object,
    item: Mapping[str, object],
    check_mode: bool,
) -> dict[str, object]:
    schema_name = validate_schema_name(validate_required_param(item, "schema"))
    grantee = validate_exact_identifier(
        validate_required_param(item, "grantee"), identifier_type="grantee"
    )
    privilege = validate_choice_param(item, "privilege", "ALL", PRIVILEGES)
    state = validate_choice_param(item, "state", DEFAULT_STATE, STATES)
    exists = _schema_grant_exists(connection, schema_name, grantee, privilege)

    if state == "absent":
        statements = (
            []
            if not exists
            else [_revoke_schema_grant_statement(schema_name, grantee, privilege)]
        )
    else:
        statements = (
            []
            if exists
            else [_grant_schema_privilege_statement(schema_name, grantee, privilege)]
        )

    if statements and not check_mode:
        common_query.execute_queries(connection, statements)

    return {
        "changed": bool(statements),
        "schema": schema_name,
        "privilege": privilege,
        "grantee": grantee,
        "granted": state == "present" if statements else exists,
        "executed_queries": statements,
    }


def _schema_grant_exists(
    connection: object,
    schema_name: str,
    grantee: str,
    privilege: str,
) -> bool:
    result = common_query.execute_queries(
        connection,
        SCHEMA_GRANT_QUERY,
        named_args={
            "schema_name": schema_name,
            "grantee": grantee,
            "privilege": privilege,
        },
    )
    return bool(result["query_result"])


def _grant_schema_privilege_statement(
    schema_name: str,
    grantee: str,
    privilege: str,
) -> str:
    quoted_schema = common_schema.quote_identifier(schema_name)
    quoted_grantee = quote_exact_identifier_value(grantee, identifier_type="grantee")
    return f"GRANT {privilege} ON SCHEMA {quoted_schema} TO {quoted_grantee}"


def _revoke_schema_grant_statement(
    schema_name: str,
    grantee: str,
    privilege: str,
) -> str:
    quoted_schema = common_schema.quote_identifier(schema_name)
    quoted_grantee = quote_exact_identifier_value(grantee, identifier_type="grantee")
    return f"REVOKE {privilege} ON SCHEMA {quoted_schema} FROM {quoted_grantee}"


def _ensure_scripts(
    connection: object,
    scripts: list[str],
    check_mode: bool,
) -> dict[str, object]:
    if not scripts:
        return {"changed": False, "executed_queries": []}

    queries = exasol_query.normalize_query_list(scripts)

    if check_mode:
        predicted = exasol_query.check_mode_result(queries)
        if predicted is not None:
            return {
                "changed": predicted["changed"],
                "executed_queries": predicted["executed_queries"],
            }

    result = exasol_query.execute_queries(connection, queries)
    return {
        "changed": result["changed"],
        "executed_queries": result["executed_queries"],
    }


def _params_with_secrets(params: Mapping[str, object]) -> dict[str, object]:
    result = dict(params)
    current_named_args = result.get("named_args")
    named_args = (
        dict(current_named_args) if isinstance(current_named_args, Mapping) else {}
    )

    for index, user in enumerate(_safe_list(params.get("users"))):
        if not isinstance(user, Mapping):
            continue
        password = user.get("password")
        ldap_dn = user.get("ldap_dn")
        if isinstance(password, str) and password:
            named_args[f"users[{index}].password"] = password
        if isinstance(ldap_dn, str) and ldap_dn:
            named_args[f"users[{index}].ldap_dn"] = ldap_dn

    result["named_args"] = named_args
    return result


def _safe_list(value: object) -> list[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return []
