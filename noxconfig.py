"""Project configuration for toolbox-provided Nox sessions."""

from __future__ import annotations

from pathlib import Path

from exasol.toolbox.config import (
    BaseConfig,
    ValidVersionStr,
)


class ProjectConfig(BaseConfig):
    """Project-specific Nox configuration."""

    ansible_test_python_versions: tuple[ValidVersionStr, ...]


PROJECT_CONFIG = ProjectConfig(
    project_name="ansible_modules",
    root_path=Path(__file__).parent,
    python_versions=("3.11", "3.12", "3.13"),
    exasol_versions=("8.29.13", "2025.1.8"),
    # The current Ansible 10 / ansible-core 2.17 test dependency does not
    # support Python 3.13. Keep ansible-test limited to supported interpreters
    # until the collection test dependency is upgraded.
    ansible_test_python_versions=("3.11", "3.12"),
)
