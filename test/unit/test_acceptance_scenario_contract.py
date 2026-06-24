"""Static checks for spec/playbook acceptance scenario contracts."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_ROOT = PROJECT_ROOT / "test" / "integration" / "acceptance"
SPEC_ROOT = PROJECT_ROOT / "specs"
SCENARIO_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")


@dataclass(frozen=True)
class Scenario:
    """Scenario identity shared by specs, playbooks, and tests."""

    scenario_id: str
    name: str


def _acceptance_contract_files() -> list[object]:
    params: list[object] = []
    for module_dir in sorted(
        path for path in ACCEPTANCE_ROOT.iterdir() if path.is_dir()
    ):
        module_name = module_dir.name
        spec_file = SPEC_ROOT / f"{module_name}.feature"
        playbook_file = module_dir / f"{module_name}_playbook.yml"
        acceptance_file = module_dir / f"test_acceptance_{module_name}.py"
        if not (
            spec_file.exists() and playbook_file.exists() and acceptance_file.exists()
        ):
            continue

        params.append(
            pytest.param(
                spec_file,
                playbook_file,
                acceptance_file,
                id=module_name,
            )
        )

    return params


@pytest.mark.parametrize(
    ("spec_file", "playbook_file", "acceptance_file"),
    _acceptance_contract_files(),
)
def test_spec_scenarios_match_playbook_scenarios(
    spec_file: Path,
    playbook_file: Path,
    acceptance_file: Path,
) -> None:
    """Every spec scenario must have one playbook block and acceptance test."""
    scenarios = _spec_scenarios(spec_file)

    assert scenarios == _playbook_scenarios(playbook_file)
    assert scenarios == _acceptance_scenarios(acceptance_file)
    _assert_scenario_ids_declared_once(playbook_file, scenarios)
    _assert_scenario_ids_declared_once(acceptance_file, scenarios)


def test_acceptance_root_contains_only_module_directories() -> None:
    """Verify acceptance modules are grouped in per-module subdirectories."""
    direct_files = [path for path in ACCEPTANCE_ROOT.iterdir() if path.is_file()]

    assert direct_files == []


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

        scenario_name = stripped.removeprefix("Scenario: ")
        assert pending_tags, f"{path}: Scenario '{scenario_name}' needs an @id tag"
        scenario_id = pending_tags[0].removeprefix("@")
        assert SCENARIO_ID_PATTERN.fullmatch(scenario_id)
        scenarios.append(Scenario(scenario_id=scenario_id, name=scenario_name))
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

        scenario_name = task.get("name")
        assert isinstance(scenario_name, str)
        assert isinstance(scenario_id, str)
        assert SCENARIO_ID_PATTERN.fullmatch(scenario_id)
        assert "tags" not in task
        assert _scenario_when_uses_current_scenario_id(task.get("when"))
        assert _scenario_result_uses_current_scenario_id(task)
        scenarios.append(Scenario(scenario_id=scenario_id, name=scenario_name))

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

        docstring = ast.get_docstring(node) or ""
        match = re.fullmatch(r"Scenario: (.+)\.", docstring)
        assert match is not None, f"{path}:{node.name} must document a scenario name"
        scenario_name = match.group(1)
        scenario_id = _acceptance_function_scenario_id(path, node)
        scenarios.append(Scenario(scenario_id=scenario_id, name=scenario_name))

    return scenarios


def _acceptance_function_scenario_id(path: Path, node: ast.FunctionDef) -> str:
    scenario_ids = {
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and SCENARIO_ID_PATTERN.fullmatch(child.value)
        and "-" in child.value
    }
    assert len(scenario_ids) == 1, f"{path}:{node.name} must reference one scenario id"
    return scenario_ids.pop()


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
