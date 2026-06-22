"""Reusable Exasol user and identifier logic."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import ModuleType

from exasol.ansible_modules.common import (
    choice_string,
    required_string,
    sibling_query_runtime,
)

MAX_IDENTIFIER_LENGTH = 128
DEFAULT_STATE = "present"
DEFAULT_UPDATE_MODE = "on_create"
DEFAULT_CASCADE = False
DEFAULT_CREATE_SESSION = True
REDACTED = "********"
USER_METADATA_QUERY = """
SELECT USER_NAME, DISTINGUISHED_NAME
FROM EXA_DBA_USERS
WHERE USER_NAME = :user_name
"""
STATES = frozenset({"present", "absent"})
UPDATE_MODES = frozenset({"always", "on_create"})
AUTHENTICATION_METHODS = frozenset({"password", "ldap"})
_REGULAR_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z]\w*$",  # re.ASCII keeps \w aligned with generated SQL rules.
    re.ASCII,
)


@dataclass(frozen=True)
class UserStatement:
    """Generated SQL with its redacted representation."""

    actual: str
    public: str


@dataclass(frozen=True)
class UserMetadata:
    """Relevant Exasol user metadata for lifecycle decisions."""

    name: str
    ldap_dn: str | None = None


def validate_schema_name(name: str) -> str:
    """Validate an Exasol schema identifier."""
    return validate_identifier(name, identifier_type="schema")


def validate_user_name(name: str) -> str:
    """Validate an Exasol user identifier."""
    return validate_identifier(name, identifier_type="user")


def validate_role_name(name: str) -> str:
    """Validate an Exasol role identifier."""
    return validate_identifier(name, identifier_type="role")


def validate_object_name(name: str, allow_qualified: bool = True) -> str:
    """Validate an Exasol object identifier, optionally schema-qualified."""
    return validate_identifier(
        name,
        identifier_type="object",
        allow_qualified=allow_qualified,
    )


def validate_identifier(
    name: str,
    identifier_type: str = "identifier",
    allow_qualified: bool = False,
) -> str:
    """Validate a conservative Exasol regular identifier.

    Exasol supports more Unicode identifier characters than this helper accepts.
    Module parameters use this conservative subset to keep generated SQL
    predictable and avoid accidental dynamic-SQL injection.
    """
    if not isinstance(name, str):
        raise ValueError(f"Exasol {identifier_type} name must be a string.")

    parts = name.split(".") if allow_qualified else [name]
    if not parts or any(part == "" for part in parts):
        raise ValueError(f"Exasol {identifier_type} name must not be empty.")

    if allow_qualified and len(parts) > 2:
        raise ValueError(
            f"Exasol {identifier_type} name must use at most schema.object "
            "qualification."
        )

    for part in parts:
        _validate_identifier_part(part, identifier_type=identifier_type)

    return name


def quote_identifier(name: str, allow_qualified: bool = False) -> str:
    """Validate and quote an Exasol regular identifier using normal uppercase."""
    validate_identifier(name, allow_qualified=allow_qualified)
    parts = name.split(".") if allow_qualified else [name]

    return ".".join(f'"{part.upper()}"' for part in parts)


def ensure_user(
    connection: object,
    params: Mapping[str, object],
    check_mode: bool = False,
) -> dict[str, object]:
    """Ensure an Exasol user is present or absent."""
    user_name = _normalized_user_name(required_string(params, "name"))
    state = _state(params)
    metadata = _user_metadata(connection, user_name)
    statements = _planned_user_statements(
        user_name=user_name,
        metadata=metadata,
        params=params,
    )

    if statements and not check_mode:
        _query_runtime().execute_queries(
            connection,
            [statement.actual for statement in statements],
        )

    return {
        "changed": bool(statements),
        "user": user_name,
        "state": state,
        "exists": state == "present" if statements else metadata is not None,
        "executed_queries": [statement.public for statement in statements],
    }


def sanitize_error_message(error: object, params: Mapping[str, object]) -> str:
    """Redact Exasol connection and user secrets from an error string."""
    return _query_runtime().sanitize_error_message(
        error,
        _params_with_user_secrets(params),
    )


def normalized_exasol_error_message(
    error: BaseException,
    params: Mapping[str, object],
    operation: str = "Exasol user management",
) -> str:
    """Return a sanitized user-facing Exasol user-management failure message."""
    return _query_runtime().normalized_exasol_error_message(
        error,
        params=_params_with_user_secrets(params),
        operation=operation,
    )


def _validate_identifier_part(part: str, identifier_type: str) -> None:
    if len(part) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"Exasol {identifier_type} identifier parts must not exceed "
            f"{MAX_IDENTIFIER_LENGTH} characters."
        )

    if not _REGULAR_IDENTIFIER_PATTERN.match(part):
        raise ValueError(
            f"Exasol {identifier_type} name '{part}' is not a valid regular "
            "identifier."
        )


def _normalized_user_name(name: str) -> str:
    return validate_user_name(name).upper()


def _user_metadata(connection: object, name: str) -> UserMetadata | None:
    result = _query_runtime().execute_queries(
        connection,
        USER_METADATA_QUERY,
        named_args={"user_name": _normalized_user_name(name)},
    )
    rows = result["query_result"]
    if not rows:
        return None

    row = rows[0]
    if not isinstance(row, Mapping):
        raise ValueError("Exasol user metadata query returned an unexpected row.")

    return UserMetadata(
        name=str(row["USER_NAME"]).upper(),
        ldap_dn=_optional_string(row.get("DISTINGUISHED_NAME")),
    )


def _planned_user_statements(
    user_name: str,
    metadata: UserMetadata | None,
    params: Mapping[str, object],
) -> list[UserStatement]:
    state = _state(params)

    if state == "absent":
        return _planned_absent_user_statements(user_name, metadata, params)

    authentication_method = _authentication_method(params)
    if metadata is None:
        return _create_user_statements(
            user_name,
            authentication=_authentication_statement(params, action="create"),
            create_session=bool(params.get("create_session", DEFAULT_CREATE_SESSION)),
        )

    if authentication_method == "ldap":
        return _planned_ldap_user_statements(user_name, metadata, params)

    if _update_password(params) == "always":
        return _planned_password_update_statements(user_name, params)

    return []


def _planned_absent_user_statements(
    user_name: str,
    metadata: UserMetadata | None,
    params: Mapping[str, object],
) -> list[UserStatement]:
    if metadata is None:
        return []

    return [
        _drop_user_statement(
            user_name,
            cascade=bool(params.get("cascade", DEFAULT_CASCADE)),
        )
    ]


def _planned_ldap_user_statements(
    user_name: str,
    metadata: UserMetadata,
    params: Mapping[str, object],
) -> list[UserStatement]:
    ldap_dn = _required_ldap_dn(params)
    if metadata.ldap_dn == ldap_dn:
        return []

    return [_alter_user_ldap_statement(user_name, ldap_dn=ldap_dn)]


def _planned_password_update_statements(
    user_name: str,
    params: Mapping[str, object],
) -> list[UserStatement]:
    return [
        _alter_user_password_statement(
            user_name,
            password=_required_password(params, action="alter"),
        )
    ]


def _create_user_statements(
    user_name: str,
    authentication: UserStatement,
    create_session: bool,
) -> list[UserStatement]:
    quoted_user = quote_identifier(user_name)
    statements = [
        UserStatement(
            actual=f"CREATE USER {quoted_user} {authentication.actual}",
            public=f"CREATE USER {quoted_user} {authentication.public}",
        )
    ]

    if create_session:
        statements.append(
            UserStatement(
                actual=f"GRANT CREATE SESSION TO {quoted_user}",
                public=f"GRANT CREATE SESSION TO {quoted_user}",
            )
        )

    return statements


def _alter_user_password_statement(user_name: str, password: str) -> UserStatement:
    quoted_user = quote_identifier(user_name)
    quoted_password = _quote_password_identifier(password)

    return UserStatement(
        actual=f"ALTER USER {quoted_user} IDENTIFIED BY {quoted_password}",
        public=f'ALTER USER {quoted_user} IDENTIFIED BY "{REDACTED}"',
    )


def _alter_user_ldap_statement(user_name: str, ldap_dn: str) -> UserStatement:
    quoted_user = quote_identifier(user_name)
    quoted_ldap_dn = _quote_sql_string_literal(ldap_dn)

    return UserStatement(
        actual=f"ALTER USER {quoted_user} IDENTIFIED AT LDAP AS {quoted_ldap_dn}",
        public=f"ALTER USER {quoted_user} IDENTIFIED AT LDAP AS '{REDACTED}'",
    )


def _drop_user_statement(user_name: str, cascade: bool) -> UserStatement:
    query = f"DROP USER {quote_identifier(user_name)}"
    if cascade:
        query = f"{query} CASCADE"

    return UserStatement(actual=query, public=query)


def _quote_password_identifier(password: str) -> str:
    if not isinstance(password, str):
        raise ValueError("Exasol user password must be a string.")

    if not password:
        raise ValueError("Exasol user password must not be empty.")

    if "\x00" in password:
        raise ValueError("Exasol user password must not contain NUL characters.")

    return f'"{_escaped_password_identifier(password)}"'


def _authentication_statement(
    params: Mapping[str, object],
    action: str,
) -> UserStatement:
    authentication_method = _authentication_method(params)

    if authentication_method == "ldap":
        return _ldap_authentication_statement(_required_ldap_dn(params))

    quoted_password = _quote_password_identifier(_required_password(params, action))
    return UserStatement(
        actual=f"IDENTIFIED BY {quoted_password}",
        public=f'IDENTIFIED BY "{REDACTED}"',
    )


def _ldap_authentication_statement(ldap_dn: str) -> UserStatement:
    quoted_ldap_dn = _quote_sql_string_literal(ldap_dn)

    return UserStatement(
        actual=f"IDENTIFIED AT LDAP AS {quoted_ldap_dn}",
        public=f"IDENTIFIED AT LDAP AS '{REDACTED}'",
    )


def _quote_sql_string_literal(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Exasol LDAP distinguished name must be a string.")

    if not value:
        raise ValueError("Exasol LDAP distinguished name must not be empty.")

    if "\x00" in value:
        raise ValueError(
            "Exasol LDAP distinguished name must not contain NUL characters."
        )

    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _state(params: Mapping[str, object]) -> str:
    return choice_string(params, "state", DEFAULT_STATE, STATES)


def _update_password(params: Mapping[str, object]) -> str:
    update_password = params.get("update_password", DEFAULT_UPDATE_MODE)

    if not isinstance(update_password, str) or update_password not in UPDATE_MODES:
        choices = ", ".join(sorted(UPDATE_MODES))
        raise ValueError(f"update_password must be one of: {choices}.")

    return update_password


def _authentication_method(params: Mapping[str, object]) -> str:
    authentication_method = params.get("authentication_method")

    if authentication_method is None:
        return "ldap" if params.get("ldap_dn") else "password"

    if (
        not isinstance(authentication_method, str)
        or authentication_method not in AUTHENTICATION_METHODS
    ):
        choices = ", ".join(sorted(AUTHENTICATION_METHODS))
        raise ValueError(f"authentication_method must be one of: {choices}.")

    return authentication_method


def _required_password(params: Mapping[str, object], action: str) -> str:
    password = params.get("password")

    if isinstance(password, str) and password:
        return password

    raise ValueError(f"password is required to {action} an Exasol user.")


def _required_ldap_dn(params: Mapping[str, object]) -> str:
    ldap_dn = params.get("ldap_dn")

    if isinstance(ldap_dn, str) and ldap_dn:
        return ldap_dn

    raise ValueError("ldap_dn is required for LDAP-authenticated Exasol users.")


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _params_with_user_secrets(params: Mapping[str, object]) -> dict[str, object]:
    result = dict(params)
    current_named_args = result.get("named_args")
    named_args = (
        dict(current_named_args) if isinstance(current_named_args, Mapping) else {}
    )
    password = params.get("password")
    ldap_dn = params.get("ldap_dn")

    if isinstance(password, str) and password:
        named_args["password"] = password
        named_args["password_sql_identifier"] = _escaped_password_identifier(password)

    if isinstance(ldap_dn, str) and ldap_dn:
        named_args["ldap_dn"] = ldap_dn
        named_args["ldap_dn_sql_literal"] = ldap_dn.replace("'", "''")
        named_args["ldap_dn_secret"] = ldap_dn
        named_args["ldap_dn_sql_literal_secret"] = ldap_dn.replace("'", "''")

    result["named_args"] = named_args
    return result


def _escaped_password_identifier(password: str) -> str:
    return password.replace('"', '""')


def _query_runtime() -> ModuleType:
    return sibling_query_runtime(__file__)
