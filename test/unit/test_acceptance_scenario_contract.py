"""Static checks for scenario-id/acceptance-test contracts."""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_ROOT = PROJECT_ROOT / "test" / "integration"
ANSIBLE_PLAYBOOK_TEST_ROOT = INTEGRATION_ROOT / "ansible_playbook"
ANSIBLE_MODULES_TEST_ROOT = INTEGRATION_ROOT / "ansible_modules"
ACCEPTANCE_COMMON_ROOT = INTEGRATION_ROOT / "acceptance_common"
SPEC_ROOT = PROJECT_ROOT / "specs"
ANSIBLE_PLAYBOOK_SPEC_ROOT = SPEC_ROOT / "ansible_playbook"
ANSIBLE_MODULES_SPEC_ROOT = SPEC_ROOT / "ansible_modules"
SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
SCENARIO_TASKS_PLACEHOLDER = "        __ACCEPTANCE_SCENARIO_TASKS__"


@dataclass(frozen=True)
class Scenario:
    """Scenario identity shared by specs, playbooks, and tests."""

    scenario_id: str


def _spec_module_names(spec_root: Path) -> set[str]:
    return {path.stem for path in spec_root.glob("*.feature")}


def _test_module_names(test_root: Path) -> set[str]:
    return {path.stem.removeprefix("test_") for path in test_root.glob("test_*.py")}


def test_ansible_playbook_specs_and_tests_are_in_sync() -> None:
    """Verify every ansible-playbook spec has a matching test, and vice versa."""
    assert _spec_module_names(ANSIBLE_PLAYBOOK_SPEC_ROOT) == _test_module_names(
        ANSIBLE_PLAYBOOK_TEST_ROOT
    )


def test_ansible_modules_specs_and_tests_are_in_sync() -> None:
    """Verify every ansible-modules spec has a matching test, and vice versa."""
    assert _spec_module_names(ANSIBLE_MODULES_SPEC_ROOT) == _test_module_names(
        ANSIBLE_MODULES_TEST_ROOT
    )


def _contract_files(spec_root: Path, test_root: Path, id_prefix: str) -> list[object]:
    params: list[object] = []
    for module_name in sorted(_spec_module_names(spec_root)):
        spec_file = spec_root / f"{module_name}.feature"
        acceptance_file = test_root / f"test_{module_name}.py"
        playbook_file = test_root / module_name / f"{module_name}_playbook.yml"
        if not acceptance_file.exists():
            continue

        params.append(
            pytest.param(
                spec_file,
                playbook_file if playbook_file.exists() else None,
                acceptance_file,
                id=f"{id_prefix}-{module_name}",
            )
        )

    return params


@pytest.mark.parametrize(
    ("spec_file", "playbook_file", "acceptance_file"),
    [
        *_contract_files(
            ANSIBLE_PLAYBOOK_SPEC_ROOT, ANSIBLE_PLAYBOOK_TEST_ROOT, "ansible_playbook"
        ),
        *_contract_files(
            ANSIBLE_MODULES_SPEC_ROOT, ANSIBLE_MODULES_TEST_ROOT, "ansible_modules"
        ),
    ],
)
def test_spec_scenarios_match_acceptance_scenarios(
    spec_file: Path,
    playbook_file: Path | None,
    acceptance_file: Path,
) -> None:
    """Every spec scenario must have a matching acceptance test."""
    scenarios = _spec_scenarios(spec_file)

    assert scenarios == _acceptance_scenarios(acceptance_file)
    _assert_scenario_ids_declared_once(acceptance_file, scenarios)
    if playbook_file is None:
        return

    assert scenarios == _playbook_scenarios(playbook_file)
    _assert_scenario_ids_declared_once(playbook_file, scenarios)


def test_ansible_playbook_root_contains_only_test_modules() -> None:
    """Verify direct ansible-playbook Python files use the test-module prefix."""
    direct_files = sorted(
        path for path in ANSIBLE_PLAYBOOK_TEST_ROOT.iterdir() if path.is_file()
    )

    assert all(
        path.suffix != ".py"
        or path.name == "__init__.py"
        or path.name.startswith("test_")
        for path in direct_files
    )


def test_ansible_playbook_spec_root_contains_only_feature_files() -> None:
    """Verify direct ansible-playbook spec files are Gherkin feature files."""
    direct_files = sorted(
        path for path in ANSIBLE_PLAYBOOK_SPEC_ROOT.iterdir() if path.is_file()
    )

    assert all(path.suffix == ".feature" for path in direct_files)


def test_ansible_modules_root_contains_only_test_modules() -> None:
    """Verify direct ansible-modules Python files use the test-module prefix."""
    direct_files = sorted(
        path for path in ANSIBLE_MODULES_TEST_ROOT.iterdir() if path.is_file()
    )

    assert all(
        path.suffix != ".py"
        or path.name == "__init__.py"
        or path.name.startswith("test_")
        for path in direct_files
    )


def test_ansible_modules_spec_root_contains_only_feature_files() -> None:
    """Verify direct ansible-modules spec files are Gherkin feature files."""
    direct_files = sorted(
        path for path in ANSIBLE_MODULES_SPEC_ROOT.iterdir() if path.is_file()
    )

    assert all(path.suffix == ".feature" for path in direct_files)


def test_acceptance_playbook_template_defines_one_scenario_placeholder() -> None:
    """Verify the shared template has one explicit scenario insertion point."""
    template = (ACCEPTANCE_COMMON_ROOT / "acceptance_playbook_template.yml").read_text(
        encoding="utf-8"
    )

    assert template.count(SCENARIO_TASKS_PLACEHOLDER) == 1
    assert "INSERT HERE" not in template


def test_acceptance_playbook_template_renders_inline_scenario_fragment() -> None:
    """Verify inline scenario fragments are inserted as valid playbook tasks."""
    acceptance_common = _acceptance_common_module()

    rendered = acceptance_common._render_template_playbook(
        """
        - name: Inline scenario
          block:
            - name: Store scenario result
              ansible.builtin.set_fact:
                acceptance_result:
                  scenario_id: "{{ acceptance_scenario_id }}"
                cacheable: true
        """,
    )
    parsed = yaml.safe_load(rendered)

    assert "__ACCEPTANCE_SCENARIO_TASKS__" not in rendered
    assert parsed[0]["tasks"][1]["block"][0]["name"] == "Inline scenario"


def test_exact_acceptance_principal_names_preserve_identifier_examples() -> None:
    """Verify exact user and role test names remain representative inputs."""
    acceptance_common = _acceptance_common_module()
    context = acceptance_common.AcceptanceContext(
        private_data_dir=Path("/tmp/private"),
        project_dir=Path("/tmp/project"),
        login_vars={},
        suffix="0123456789ABCDEF0123456789ABCDEF",
    )

    assert (
        context.exact_test_user
        == "ANSIBLE_USER_EXACT+/=User_0123456789ABCDEF0123456789ABCDEF"
    )
    assert (
        context.exact_test_role
        == "ANSIBLE_ROLE_EXACT+/=Role_0123456789ABCDEF0123456789ABCDEF"
    )
    assert (
        acceptance_common._quote_cleanup_identifier(context.exact_test_role.upper())
        == f'"{context.exact_test_role.upper()}"'
    )


class FakeConnection:
    """Small pyexasol connection stand-in for cleanup tests."""

    def __init__(self) -> None:
        self.executed: list[str] = []
        self.closed = False

    def execute(self, query: str) -> None:
        self.executed.append(query)

    def close(self) -> None:
        self.closed = True


class FakeQueryResult:
    """Small fetchall wrapper for catalog query tests."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[dict[str, str]]:
        return self._rows


class FakeCatalogConnection(FakeConnection):
    """Connection stand-in with deterministic catalog query results."""

    def __init__(self, results: dict[str, list[dict[str, str]]]) -> None:
        super().__init__()
        self._results = results

    def execute(self, query: str) -> FakeQueryResult | None:
        normalized_query = " ".join(query.split())
        self.executed.append(normalized_query)
        rows = self._results.get(normalized_query)
        if rows is None:
            return None
        return FakeQueryResult(rows)


def test_cleanup_database_objects_drops_all_non_system_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acceptance_common = _acceptance_common_module()
    connection = FakeConnection()

    monkeypatch.setattr(
        acceptance_common, "connect_to_exasol", lambda login_vars: connection
    )
    monkeypatch.setattr(
        acceptance_common,
        "_schema_names_to_drop",
        lambda _: ("APP_SCHEMA", "Mixed Case Schema"),
    )
    monkeypatch.setattr(
        acceptance_common,
        "_user_names_to_drop",
        lambda _, current_user: ("APP_USER",) if current_user == "SYS" else (),
    )
    monkeypatch.setattr(
        acceptance_common,
        "_role_names_to_drop",
        lambda _: ("APP_ROLE",),
    )

    acceptance_common.cleanup_database_objects({"login_user": "SYS"})

    assert connection.executed == [
        'DROP SCHEMA "APP_SCHEMA" CASCADE',
        'DROP SCHEMA "Mixed Case Schema" CASCADE',
        'DROP USER "APP_USER" CASCADE',
        'DROP ROLE "APP_ROLE" CASCADE',
    ]
    assert connection.closed is True


def test_cleanup_database_object_filters_skip_system_principals() -> None:
    acceptance_common = _acceptance_common_module()
    connection = FakeCatalogConnection(
        {
            "SELECT SCHEMA_NAME FROM EXA_ALL_SCHEMAS": [
                {"SCHEMA_NAME": "SYS"},
                {"SCHEMA_NAME": "EXA_STATISTICS"},
                {"SCHEMA_NAME": "APP_SCHEMA"},
            ],
            "SELECT USER_NAME FROM EXA_ALL_USERS": [
                {"USER_NAME": "SYS"},
                {"USER_NAME": "service_admin"},
                {"USER_NAME": "APP_USER"},
            ],
            "SELECT ROLE_NAME FROM EXA_ALL_ROLES": [
                {"ROLE_NAME": "PUBLIC"},
                {"ROLE_NAME": "DBA"},
                {"ROLE_NAME": "APP_ROLE"},
            ],
        }
    )

    assert acceptance_common._schema_names_to_drop(connection) == (
        "SYS",
        "EXA_STATISTICS",
        "APP_SCHEMA",
    )
    assert acceptance_common._user_names_to_drop(connection, "service_admin") == (
        "APP_USER",
    )
    assert acceptance_common._role_names_to_drop(connection) == ("APP_ROLE",)


def _acceptance_common_module() -> Any:
    if str(INTEGRATION_ROOT) not in sys.path:
        sys.path.insert(0, str(INTEGRATION_ROOT))

    from acceptance_common import acceptance_test_common

    return acceptance_test_common


def _spec_scenarios(path: Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    pending_tags: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            pending_tags = stripped.split()
            continue

        if not stripped.startswith("Scenario: "):
            continue

        assert pending_tags, f"{path}: Scenario '{stripped}' needs an @id tag"
        scenario_id = pending_tags[0].removeprefix("@")
        assert SCENARIO_ID_PATTERN.fullmatch(scenario_id)
        scenarios.append(Scenario(scenario_id=scenario_id))
        pending_tags = []

    return scenarios


def _playbook_scenarios(path: Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for task in _walk_tasks(
        yaml.safe_load(path.read_text(encoding="utf-8"))[0]["tasks"]
    ):
        scenario_id = task.get("vars", {}).get("acceptance_current_scenario_id")
        if scenario_id is None:
            continue

        assert isinstance(scenario_id, str)
        assert SCENARIO_ID_PATTERN.fullmatch(scenario_id)
        assert "tags" not in task
        assert _scenario_when_uses_current_scenario_id(task.get("when"))
        assert _scenario_result_uses_current_scenario_id(task)
        scenarios.append(Scenario(scenario_id=scenario_id))

    return scenarios


def _scenario_when_uses_current_scenario_id(when: object) -> bool:
    expression = when[0] if isinstance(when, list) else when
    if not isinstance(expression, str):
        return False

    return (
        "acceptance_scenario_id" in expression
        and "acceptance_current_scenario_id" in expression
    )


def _scenario_result_uses_current_scenario_id(task: dict[str, Any]) -> bool:
    result_task_count = 0
    for child in _walk_tasks(task.get("block", [])):
        set_fact = child.get("ansible.builtin.set_fact", {})
        if not isinstance(set_fact, dict) or "acceptance_result" not in set_fact:
            continue

        result_task_count += 1
        scenario_id = set_fact["acceptance_result"].get("scenario_id")
        assert scenario_id == "{{ acceptance_current_scenario_id }}"

    return result_task_count == 1


def _acceptance_scenarios(path: Path) -> list[Scenario]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scenarios: list[Scenario] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue

        scenario_id = _acceptance_function_scenario_id(path, node)
        scenarios.append(Scenario(scenario_id=scenario_id))

    return scenarios


def _acceptance_function_scenario_id(path: Path, node: ast.FunctionDef) -> str:
    scenario_ids = [
        scenario_id
        for decorator in node.decorator_list
        if (scenario_id := _scenario_id_marker_value(decorator)) is not None
    ]
    assert (
        len(scenario_ids) == 1
    ), f"{path}:{node.name} must declare one scenario_id marker"
    scenario_id = scenario_ids[0]
    assert (
        SCENARIO_ID_PATTERN.fullmatch(scenario_id) and "-" in scenario_id
    ), f"{path}:{node.name} has invalid scenario id {scenario_id}"
    return scenario_id


def _scenario_id_marker_value(decorator: ast.expr) -> str | None:
    if (
        not isinstance(decorator, ast.Call)
        or len(decorator.args) != 1
        or decorator.keywords
    ):
        return None

    marker = decorator.func
    if not (
        isinstance(marker, ast.Attribute)
        and marker.attr == "scenario_id"
        and isinstance(marker.value, ast.Attribute)
        and marker.value.attr == "mark"
        and isinstance(marker.value.value, ast.Name)
        and marker.value.value.id == "pytest"
    ):
        return None

    value = decorator.args[0]
    return (
        value.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
        else None
    )


def _assert_scenario_ids_declared_once(path: Path, scenarios: list[Scenario]) -> None:
    content = path.read_text(encoding="utf-8")
    for scenario in scenarios:
        pattern = re.compile(
            rf"(?<![a-z0-9-]){re.escape(scenario.scenario_id)}(?![a-z0-9-])"
        )
        count = len(pattern.findall(content))
        assert count == 1, (
            f"{path}: scenario id {scenario.scenario_id} must be declared once, "
            f"found {count}"
        )


def _walk_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    walked: list[dict[str, Any]] = []
    for task in tasks:
        walked.append(task)
        if block := task.get("block"):
            walked.extend(_walk_tasks(block))
    return walked
