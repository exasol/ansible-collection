"""Project configuration for toolbox-provided Nox sessions."""

from __future__ import annotations

from pathlib import Path

from exasol.toolbox.config import BaseConfig

PROJECT_CONFIG = BaseConfig(
    project_name="ansible_modules",
    root_path=Path(__file__).parent,
    python_versions=("3.11", "3.12", "3.13", "3.14"),
    exasol_versions=("8.29.13", "2025.1.8"),
)
