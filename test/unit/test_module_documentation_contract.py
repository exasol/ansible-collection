"""Static module documentation contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "module_path",
    [
        PROJECT_ROOT / "plugins" / "modules" / "exasol_grants.py",
        PROJECT_ROOT / "plugins" / "modules" / "exasol_query.py",
        PROJECT_ROOT / "plugins" / "modules" / "exasol_role.py",
        PROJECT_ROOT / "plugins" / "modules" / "exasol_user.py",
    ],
)
def test_module_defines_documentation_examples_and_return(module_path: Path) -> None:
    """Verify public Ansible modules expose required documentation constants."""
    assignments = _top_level_string_assignments(module_path)

    assert assignments["DOCUMENTATION"].strip()
    assert assignments["EXAMPLES"].strip()
    assert assignments["RETURN"].strip()


def test_connection_documented_modules_are_in_connection_action_group() -> None:
    """Verify connection module defaults apply to all connection modules."""
    runtime = yaml.safe_load(
        (PROJECT_ROOT / "meta" / "runtime.yml").read_text(encoding="utf-8")
    )
    connection_group = set(runtime["action_groups"]["connection"])

    for module_path in (PROJECT_ROOT / "plugins" / "modules").glob("exasol_*.py"):
        assignments = _top_level_string_assignments(module_path)
        if "exasol.exasol.connection" not in assignments["DOCUMENTATION"]:
            continue

        module_name = module_path.stem
        assert f"exasol.exasol.{module_name}" in connection_group


def _top_level_string_assignments(module_path: Path) -> dict[str, str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    assignments: dict[str, str] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                if isinstance(node.value.value, str):
                    assignments[target.id] = node.value.value

    return assignments
