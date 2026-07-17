"""Static module documentation contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = PROJECT_ROOT / "plugins" / "modules"


@pytest.mark.parametrize(
    "module_path",
    [
        pytest.param(module_path, id=module_path.stem)
        for module_path in sorted(MODULE_DIR.glob("exasol_*.py"))
    ],
)
def test_module_defines_documentation_examples_and_return(module_path: Path) -> None:
    """Verify public Ansible modules expose required documentation constants."""
    assignments = _top_level_string_assignments(module_path)

    assert assignments["DOCUMENTATION"].strip()
    assert assignments["EXAMPLES"].strip()
    assert assignments["RETURN"].strip()


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
