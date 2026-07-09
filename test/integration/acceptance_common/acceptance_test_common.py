"""Shared helpers for feature-level Ansible acceptance tests."""

from __future__ import annotations

import json
import re
import sys
import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exasol.ansible.playbook import Playbook
from exasol.ansible.runner import Runner
from exasol.ansible_modules.common_identifier_validation import quote_identifier
from exasol.ansible_modules.common_query import (
    build_exasol_connect_kwargs,
    normalized_exasol_error_message,
)
from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
ACCEPTANCE_COMMON_DIR = PROJECT_ROOT / "test" / "integration" / "acceptance_common"
ACCEPTANCE_PLAYBOOK_TEMPLATE = (
    ACCEPTANCE_COMMON_DIR / "acceptance_playbook_template.yml"
)
SCENARIO_TASKS_PLACEHOLDER = "        __ACCEPTANCE_SCENARIO_TASKS__"
DISPOSABLE_SCHEMA_PATTERN = re.compile(r"^ANSIBLE_SCHEMA_[0-9A-F]{32}(?:_CHECK_MODE)?$")
DISPOSABLE_USER_PATTERN = re.compile(r"^ANSIBLE_USER(?:_CHECK)?_[0-9A-F]{32}$")
DISPOSABLE_ROLE_PATTERN = re.compile(r"^ANSIBLE_ROLE(?:_CHECK)?_[0-9A-F]{32}$")


@dataclass(frozen=True)
class AcceptanceContext:
    """Inputs needed to run one generated acceptance playbook."""

    private_data_dir: Path
    project_dir: Path
    login_vars: dict[str, object]
    suffix: str
    python_interpreter: Path | None = None

    @property
    def test_schema(self) -> str:
        return f"ANSIBLE_SCHEMA_{self.suffix}"

    @property
    def test_user(self) -> str:
        return f"ANSIBLE_USER_{self.suffix}"

    @property
    def check_mode_user(self) -> str:
        return f"ANSIBLE_USER_CHECK_{self.suffix}"

    @property
    def test_role(self) -> str:
        return f"ANSIBLE_ROLE_{self.suffix}"

    @property
    def check_mode_role(self) -> str:
        return f"ANSIBLE_ROLE_CHECK_{self.suffix}"

    @property
    def test_user_password(self) -> str:
        return f"Initial_{self.suffix}"

    @property
    def test_user_rotated_password(self) -> str:
        return f"Rotated_{self.suffix}"

    @property
    def check_mode_user_password(self) -> str:
        return f"Check_{self.suffix}"

    @property
    def invalid_login_password(self) -> str:
        return f"invalid-{self.suffix.lower()}"

    @property
    def test_user_ldap_dn(self) -> str:
        return f"cn={self.test_user.lower()},dc=authorization,dc=exasol,dc=com"

    @property
    def check_mode_user_ldap_dn(self) -> str:
        return f"cn={self.check_mode_user.lower()},dc=authorization,dc=exasol,dc=com"

    @property
    def playbook_vars(self) -> dict[str, object]:
        return {
            **self.login_vars,
            "ansible_python_interpreter": (
                str(self.python_interpreter)
                if self.python_interpreter
                else sys.executable
            ),
            "test_schema": self.test_schema,
            "test_user": self.test_user,
            "check_mode_user": self.check_mode_user,
            "test_role": self.test_role,
            "check_mode_role": self.check_mode_role,
            "test_user_password": self.test_user_password,
            "test_user_rotated_password": self.test_user_rotated_password,
            "check_mode_user_password": self.check_mode_user_password,
            "invalid_login_password": self.invalid_login_password,
            "test_user_ldap_dn": self.test_user_ldap_dn,
            "check_mode_user_ldap_dn": self.check_mode_user_ldap_dn,
        }


def given_acceptance_context(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    python_interpreter: Path | None = None,
) -> AcceptanceContext:
    """Given a unique disposable acceptance-test namespace."""
    return AcceptanceContext(
        private_data_dir=ansible_runner_workspace.private_data_dir,
        project_dir=ansible_runner_workspace.project_dir,
        login_vars=exasol_login_vars,
        suffix=uuid.uuid4().hex.upper(),
        python_interpreter=python_interpreter,
    )


def acceptance_playbook_resource(module_name: str) -> Path:
    """Return the acceptance playbook resource path for a module."""
    return (
        PROJECT_ROOT
        / "test"
        / "integration"
        / "acceptance"
        / module_name
        / f"{module_name}_playbook.yml"
    )


def when_acceptance_scenario_runs(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
    module_name: str,
    scenario_id: str,
    extra_vars: dict[str, object] | None = None,
) -> dict[str, Any]:
    """When one module acceptance scenario runs with a fresh context."""
    context = given_acceptance_context(ansible_runner_workspace, exasol_login_vars)
    return when_module_scenario_runs(
        context,
        module_name,
        scenario_id,
        extra_vars=extra_vars,
    )


def when_module_scenario_runs(
    context: AcceptanceContext,
    module_name: str,
    scenario_id: str,
    *,
    scenario_playbook: str | None = None,
    extra_vars: dict[str, object] | None = None,
) -> dict[str, Any]:
    """When one module acceptance scenario runs with an existing context."""
    if scenario_playbook is not None:
        return when_template_scenario_runs(
            context,
            module_name,
            scenario_id,
            scenario_playbook,
            extra_vars=extra_vars,
        )

    return when_playbook_scenario_runs(
        context,
        acceptance_playbook_resource(module_name),
        scenario_id,
        extra_vars=extra_vars,
    )


def when_template_scenario_runs(
    context: AcceptanceContext,
    module_name: str,
    scenario_id: str,
    scenario_playbook: str,
    extra_vars: dict[str, object] | None = None,
) -> dict[str, Any]:
    """When one inline scenario fragment runs through the shared template."""
    playbook = _write_template_playbook(
        context.project_dir,
        module_name,
        scenario_id,
        scenario_playbook,
    )
    return _run_playbook(context, playbook, scenario_id, extra_vars=extra_vars)


def when_playbook_scenario_runs(
    context: AcceptanceContext,
    playbook_resource: Path,
    scenario_id: str,
    extra_vars: dict[str, object] | None = None,
) -> dict[str, Any]:
    """When one playbook-defined acceptance scenario runs."""
    playbook = _write_playbook(
        context.project_dir,
        playbook_resource,
        scenario_id,
    )
    return _run_playbook(context, playbook, scenario_id, extra_vars=extra_vars)


def _run_playbook(
    context: AcceptanceContext,
    playbook: Path,
    scenario_id: str,
    extra_vars: dict[str, object] | None = None,
) -> dict[str, Any]:
    runner = Runner(
        repositories=(),
        work_dir=context.private_data_dir,
    )
    facts = runner.run(
        Playbook(
            playbook.relative_to(context.project_dir).as_posix(),
            {
                **context.playbook_vars,
                "acceptance_scenario_id": scenario_id,
                **(extra_vars or {}),
            },
        ),
        retrieve_facts_from="localhost",
    )

    result = facts["acceptance_result"]
    assert result.get("scenario_id") == scenario_id

    return _without_scenario_id(result)


def then_result_matches(result: dict[str, Any], expected: dict[str, Any]) -> None:
    """Then the scenario result exactly matches the expected public contract."""
    assert result == expected


def then_secret_is_not_exposed(result: dict[str, Any], secret: str) -> None:
    """Then a known secret value is absent from the JSON-serializable result."""
    assert secret not in json.dumps(result)


def _write_playbook(
    project_dir: Path,
    playbook_resource: Path,
    scenario_id: str,
) -> Path:
    _assert_playbook_contains_scenario(playbook_resource, scenario_id)
    playbook_dir = project_dir / playbook_resource.parent.name
    playbook_dir.mkdir(exist_ok=True)
    playbook = playbook_dir / f"{scenario_id}.yml"
    playbook.write_text(
        playbook_resource.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return playbook


def _write_template_playbook(
    project_dir: Path,
    module_name: str,
    scenario_id: str,
    scenario_playbook: str,
) -> Path:
    playbook_dir = project_dir / module_name
    playbook_dir.mkdir(exist_ok=True)
    playbook = playbook_dir / f"{scenario_id}.yml"
    rendered_playbook = _render_template_playbook(scenario_playbook)
    playbook.write_text(rendered_playbook, encoding="utf-8")
    return playbook


def _render_template_playbook(scenario_playbook: str) -> str:
    template = ACCEPTANCE_PLAYBOOK_TEMPLATE.read_text(encoding="utf-8")
    scenario_tasks = textwrap.indent(
        textwrap.dedent(scenario_playbook).strip("\n"),
        " " * 8,
    )
    if SCENARIO_TASKS_PLACEHOLDER not in template:
        msg = f"{ACCEPTANCE_PLAYBOOK_TEMPLATE} does not define scenario placeholder"
        raise AssertionError(msg)
    return template.replace(SCENARIO_TASKS_PLACEHOLDER, scenario_tasks)


def _assert_playbook_contains_scenario(
    playbook_resource: Path, scenario_id: str
) -> None:
    content = playbook_resource.read_text(encoding="utf-8")
    scenario_id_variable = f"acceptance_current_scenario_id: {scenario_id}"
    if scenario_id_variable not in content:
        msg = f"{playbook_resource} does not define scenario id {scenario_id}"
        raise AssertionError(msg)


def _without_scenario_id(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "scenario_id"}


def cleanup_disposable_database_objects(login_vars: dict[str, object]) -> None:
    """Delete disposable schemas, users, and roles created by integration tests."""
    try:
        connection = connect_to_exasol(login_vars)
        try:
            for schema_name in _matching_schema_names(connection):
                connection.execute(
                    f"DROP SCHEMA {quote_identifier(schema_name)} CASCADE"
                )
            for user_name in _matching_user_names(connection):
                connection.execute(f"DROP USER {quote_identifier(user_name)} CASCADE")
            for role_name in _matching_role_names(connection):
                connection.execute(f"DROP ROLE {quote_identifier(role_name)} CASCADE")
        finally:
            connection.close()
    except Exception as error:
        message = normalized_exasol_error_message(
            error,
            login_vars,
            operation="Acceptance cleanup",
        )
        raise AssertionError(message) from error


def connect_to_exasol(login_vars: dict[str, object]) -> Any:
    import pyexasol

    return pyexasol.connect(**build_exasol_connect_kwargs(login_vars))


def _matching_schema_names(connection: Any) -> tuple[str, ...]:
    return _matching_object_names(
        connection,
        catalog_column="SCHEMA_NAME",
        catalog_table="EXA_ALL_SCHEMAS",
        like_pattern="ANSIBLE_SCHEMA_%",
        name_pattern=DISPOSABLE_SCHEMA_PATTERN,
        object_kind="schema",
    )


def _matching_user_names(connection: Any) -> tuple[str, ...]:
    return _matching_object_names(
        connection,
        catalog_column="USER_NAME",
        catalog_table="EXA_ALL_USERS",
        like_pattern="ANSIBLE_USER%",
        name_pattern=DISPOSABLE_USER_PATTERN,
        object_kind="user",
    )


def _matching_role_names(connection: Any) -> tuple[str, ...]:
    return _matching_object_names(
        connection,
        catalog_column="ROLE_NAME",
        catalog_table="EXA_ALL_ROLES",
        like_pattern="ANSIBLE_ROLE%",
        name_pattern=DISPOSABLE_ROLE_PATTERN,
        object_kind="role",
    )


def _matching_object_names(
    connection: Any,
    *,
    catalog_column: str,
    catalog_table: str,
    like_pattern: str,
    name_pattern: re.Pattern[str],
    object_kind: str,
) -> tuple[str, ...]:
    rows = connection.execute(f"""
        SELECT {catalog_column}
        FROM {catalog_table}
        WHERE {catalog_column} LIKE '{like_pattern}'
        """).fetchall()
    names = []
    for row in rows:
        name = str(_row_value(row, catalog_column, 0))
        if not name_pattern.fullmatch(name):
            msg = f"Unsafe disposable acceptance {object_kind} name: {name}"
            raise AssertionError(msg)
        names.append(name)
    return tuple(names)


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]
    return row[index]
