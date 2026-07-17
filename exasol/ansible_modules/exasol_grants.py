"""Reusable Exasol grant-management logic."""

from __future__ import annotations

from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import dataclass

from exasol.ansible_modules import common_query
from exasol.ansible_modules.common_identifier_validation import (
    quote_exact_identifier_value,
    quote_identifier,
    validate_identifier,
    validate_object_name,
    validate_role_name,
    validate_user_name,
)
from exasol.ansible_modules.common_param_validation import validate_choice_param

DEFAULT_STATE = "present"
STATES = frozenset({"present", "absent"})

SYSTEM_PRIVILEGES = frozenset(
    {
        "ACCESS ANY CONNECTION",
        "ALTER ANY CONNECTION",
        "ALTER ANY SCHEMA",
        "ALTER ANY TABLE",
        "ALTER ANY VIRTUAL SCHEMA",
        "ALTER ANY VIRTUAL SCHEMA REFRESH",
        "ALTER SYSTEM",
        "ALTER USER",
        "CREATE ANY FUNCTION",
        "CREATE ANY SCRIPT",
        "CREATE ANY TABLE",
        "CREATE ANY VIEW",
        "CREATE CONNECTION",
        "CREATE FUNCTION",
        "CREATE ROLE",
        "CREATE SCHEMA",
        "CREATE SCRIPT",
        "CREATE SESSION",
        "CREATE TABLE",
        "CREATE USER",
        "CREATE VIEW",
        "CREATE VIRTUAL SCHEMA",
        "DELETE ANY TABLE",
        "DROP ANY CONNECTION",
        "DROP ANY FUNCTION",
        "DROP ANY ROLE",
        "DROP ANY SCHEMA",
        "DROP ANY SCRIPT",
        "DROP ANY TABLE",
        "DROP ANY VIEW",
        "DROP ANY VIRTUAL SCHEMA",
        "DROP USER",
        "EXECUTE ANY FUNCTION",
        "EXECUTE ANY SCRIPT",
        "EXPORT",
        "GRANT ANY CONNECTION",
        "GRANT ANY OBJECT PRIVILEGE",
        "GRANT ANY PRIVILEGE",
        "GRANT ANY ROLE",
        "IMPERSONATE ANY USER",
        "IMPORT",
        "INSERT ANY TABLE",
        "KILL ANY SESSION",
        "MANAGE CONSUMER GROUPS",
        "SELECT ANY DICTIONARY",
        "SELECT ANY TABLE",
        "SET ANY CONSUMER GROUP",
        "UPDATE ANY TABLE",
        "USE ANY CONNECTION",
        "USE ANY SCHEMA",
    }
)
OBJECT_PRIVILEGES = frozenset(
    {
        "ACCESS",
        "ALTER",
        "DELETE",
        "EXECUTE",
        "IMPERSONATION",
        "INSERT",
        "REFERENCES",
        "REFRESH",
        "SELECT",
        "UPDATE",
        "USAGE",
    }
)
OBJECT_TYPE_SQL = {
    "function": "FUNCTION",
    "script": "SCRIPT",
    "table": "TABLE",
    "view": "VIEW",
    "virtual_schema": "VIRTUAL SCHEMA",
}

SYSTEM_PRIVILEGE_EXISTS_QUERY = """
SELECT PRIVILEGE
FROM EXA_DBA_SYS_PRIVS
WHERE UPPER(GRANTEE) = UPPER(:principal)
AND PRIVILEGE = :privilege
"""

OBJECT_PRIVILEGE_EXISTS_QUERY = """
SELECT PRIVILEGE
FROM EXA_DBA_OBJ_PRIVS
WHERE UPPER(GRANTEE) = UPPER(:principal)
AND PRIVILEGE = :privilege
AND (
    (
        :object_name IS NULL
        AND UPPER(COALESCE(OBJECT_SCHEMA, OBJECT_NAME)) = UPPER(:schema_name)
        AND (OBJECT_NAME IS NULL OR UPPER(OBJECT_NAME) = UPPER(:schema_name))
    )
    OR (
        :object_name IS NOT NULL
        AND UPPER(OBJECT_SCHEMA) = UPPER(:schema_name)
        AND UPPER(OBJECT_NAME) = UPPER(:object_name)
    )
)
AND (:object_type IS NULL OR UPPER(OBJECT_TYPE) = UPPER(:object_type))
"""


@dataclass(frozen=True)
class Principal:
    """Selected user or role receiving grant-management changes."""

    principal_type: str
    name: str

    @property
    def quoted(self) -> str:
        """Return the principal rendered as an exact Exasol SQL identifier."""
        return quote_exact_identifier_value(
            self.name,
            identifier_type=self.principal_type,
        )


@dataclass(frozen=True)
class SystemGrant:
    """Requested system privilege state."""

    privilege: str


@dataclass(frozen=True)
class ObjectGrant:
    """Requested schema-scoped object privilege state."""

    privilege: str
    schema_name: str
    object_name: str | None = None
    object_type: str | None = None


GrantRequest = SystemGrant | ObjectGrant


@dataclass(frozen=True)
class GrantStatement:
    """Generated grant-management SQL statement."""

    query: str


def ensure_grants(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure requested Exasol privileges are present or absent."""
    principal = _principal(params)
    state = _state(params)
    requests = _grant_requests(params)
    statements = _planned_grant_statements(
        connection=connection,
        principal=principal,
        requests=requests,
        state=state,
    )

    if statements and not check_mode:
        common_query.execute_queries(
            connection,
            [statement.query for statement in statements],
        )

    return {
        "changed": bool(statements),
        "principal": principal.name,
        "principal_type": principal.principal_type,
        "state": state,
        "executed_queries": [statement.query for statement in statements],
    }


def module_argument_spec() -> dict[str, object]:
    """Return the Ansible-facing argument spec for the grants module."""
    return {
        **common_query.exasol_connection_argument_spec(),
        "user": {"type": "str"},
        "role": {"type": "str"},
        "state": {
            "type": "str",
            "choices": sorted(STATES),
            "default": DEFAULT_STATE,
        },
        "system_privileges": {
            "type": "list",
            "elements": "str",
        },
        "object_privileges": {
            "type": "list",
            "elements": "dict",
            "options": {
                "schema": {"type": "str", "required": True},
                "object": {"type": "str"},
                "object_type": {
                    "type": "str",
                    "choices": sorted(OBJECT_TYPE_SQL),
                },
                "privileges": {
                    "type": "list",
                    "elements": "str",
                    "required": True,
                },
            },
        },
    }


def run_grants(
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Connect to Exasol and manage the requested grants."""
    with common_query.connect_to_exasol(
        params,
        module_name="exasol_grants",
    ) as connection:
        return ensure_grants(connection, params, check_mode=check_mode)


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact sensitive data from an error message."""
    return common_query.sanitize_error_message(error, params)


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol grant management",
) -> str:
    """Return sanitized user-facing error message."""
    return common_query.normalized_exasol_error_message(
        error,
        params=params,
        operation=operation,
    )


def _planned_grant_statements(
    connection: object,
    principal: Principal,
    requests: Sequence[GrantRequest],
    state: str,
) -> list[GrantStatement]:
    statements: list[GrantStatement] = []

    for request in requests:
        grant_exists = _grant_exists(connection, principal, request)
        if state == "present" and not grant_exists:
            statements.append(GrantStatement(_grant_query(principal, request)))
        elif state == "absent" and grant_exists:
            statements.append(GrantStatement(_revoke_query(principal, request)))

    return statements


def _grant_exists(
    connection: object,
    principal: Principal,
    request: GrantRequest,
) -> bool:
    if isinstance(request, SystemGrant):
        return _system_grant_exists(connection, principal, request)

    return _object_grant_exists(connection, principal, request)


def _system_grant_exists(
    connection: object,
    principal: Principal,
    request: SystemGrant,
) -> bool:
    result = common_query.execute_queries(
        connection,
        SYSTEM_PRIVILEGE_EXISTS_QUERY,
        named_args={
            "principal": principal.name,
            "privilege": request.privilege,
        },
    )
    return bool(result["query_result"])


def _object_grant_exists(
    connection: object,
    principal: Principal,
    request: ObjectGrant,
) -> bool:
    result = common_query.execute_queries(
        connection,
        OBJECT_PRIVILEGE_EXISTS_QUERY,
        named_args={
            "principal": principal.name,
            "privilege": request.privilege,
            "schema_name": request.schema_name,
            "object_name": request.object_name,
            "object_type": _metadata_object_type(request),
        },
    )
    return bool(result["query_result"])


def _grant_query(principal: Principal, request: GrantRequest) -> str:
    if isinstance(request, SystemGrant):
        return f"GRANT {request.privilege} TO {principal.quoted}"

    return (
        f"GRANT {request.privilege} ON {_object_target(request)} "
        f"TO {principal.quoted}"
    )


def _revoke_query(principal: Principal, request: GrantRequest) -> str:
    if isinstance(request, SystemGrant):
        return f"REVOKE {request.privilege} FROM {principal.quoted}"

    return (
        f"REVOKE {request.privilege} ON {_object_target(request)} "
        f"FROM {principal.quoted}"
    )


def _object_target(request: ObjectGrant) -> str:
    schema = quote_identifier(request.schema_name)

    if request.object_name is None:
        return schema

    target = f"{schema}.{quote_identifier(request.object_name)}"
    object_type = _object_type_sql(request.object_type)

    if object_type is None:
        return target

    return f"{object_type} {target}"


def _metadata_object_type(request: ObjectGrant) -> str | None:
    return _object_type_sql(request.object_type)


def _principal(params: Mapping[str, object]) -> Principal:
    user = params.get("user")
    role = params.get("role")
    has_user = user is not None
    has_role = role is not None

    if has_user == has_role:
        raise ValueError("exactly one of user or role must be supplied.")

    if has_user:
        return Principal(
            principal_type="user",
            name=validate_user_name(_non_empty_string(user, "user")),
        )

    return Principal(
        principal_type="role",
        name=validate_role_name(_non_empty_string(role, "role")),
    )


def _grant_requests(params: Mapping[str, object]) -> list[GrantRequest]:
    requests: list[GrantRequest] = [
        SystemGrant(privilege)
        for privilege in _privilege_list(
            params.get("system_privileges"),
            option_name="system_privileges",
            allowed=SYSTEM_PRIVILEGES,
            privilege_type="system",
        )
    ]

    for index, item in enumerate(_object_privilege_items(params)):
        requests.extend(_object_grant_requests(item, index))

    if not requests:
        raise ValueError(
            "at least one of system_privileges or object_privileges must contain "
            "a privilege."
        )

    return _deduplicate_requests(requests)


def _object_grant_requests(
    item: Mapping[str, object],
    index: int,
) -> list[ObjectGrant]:
    prefix = f"object_privileges[{index}]"
    schema_name = validate_identifier(
        _non_empty_string(item.get("schema"), "schema"),
        identifier_type="schema",
    )
    object_name = _optional_object_name(item.get("object"))
    object_type = _object_type(item.get("object_type"))
    privileges = _privilege_list(
        item.get("privileges"),
        option_name=f"{prefix}.privileges",
        allowed=OBJECT_PRIVILEGES,
        privilege_type="object",
    )

    return [
        ObjectGrant(
            privilege=privilege,
            schema_name=schema_name,
            object_name=object_name,
            object_type=object_type,
        )
        for privilege in privileges
    ]


def _object_privilege_items(params: Mapping[str, object]) -> list[Mapping[str, object]]:
    value = params.get("object_privileges")

    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError("object_privileges must be a list of dictionaries.")

    if not value:
        raise ValueError("object_privileges must not be empty when supplied.")

    items: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"object_privileges[{index}] must be a dictionary.")
        items.append(item)

    return items


def _privilege_list(
    value: object,
    *,
    option_name: str,
    allowed: frozenset[str],
    privilege_type: str,
) -> list[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError(f"{option_name} must be a list of strings.")

    if not value:
        raise ValueError(f"{option_name} must not be empty when supplied.")

    return [
        _normalize_privilege(item, allowed=allowed, privilege_type=privilege_type)
        for item in value
    ]


def _normalize_privilege(
    privilege: object,
    *,
    allowed: frozenset[str],
    privilege_type: str,
) -> str:
    name = _non_empty_string(privilege, f"{privilege_type} privilege")
    normalized = " ".join(name.upper().split())

    if normalized not in allowed:
        raise ValueError(f"unsupported Exasol {privilege_type} privilege {name!r}.")

    return normalized


def _optional_object_name(value: object) -> str | None:
    if value is None:
        return None

    return validate_object_name(
        _non_empty_string(value, "object"), allow_qualified=False
    )


def _object_type(value: object) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("object_type must be a string.")

    if value not in OBJECT_TYPE_SQL:
        choices = ", ".join(sorted(OBJECT_TYPE_SQL))
        raise ValueError(f"object_type must be one of: {choices}. Got: {value!r}.")

    return value


def _object_type_sql(value: str | None) -> str | None:
    if value is None:
        return None

    return OBJECT_TYPE_SQL[value]


def _state(params: Mapping[str, object]) -> str:
    return validate_choice_param(params, "state", DEFAULT_STATE, STATES)


def _non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string.")

    return value


def _deduplicate_requests(requests: Sequence[GrantRequest]) -> list[GrantRequest]:
    deduplicated: list[GrantRequest] = []
    seen: set[GrantRequest] = set()

    for request in requests:
        if request in seen:
            continue
        seen.add(request)
        deduplicated.append(request)

    return deduplicated
