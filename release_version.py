"""Helpers for keeping release version metadata synchronized."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

RUNTIME_PACKAGE_NAME = "exasol-ansible-modules"


def load_project_version(project_root: Path) -> str:
    """Return the authoritative project version from pyproject.toml."""
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text())
    return pyproject["project"]["version"]


def format_runtime_requirement(version: str) -> str:
    """Return the exact runtime requirement line for a collection release."""
    return f"{RUNTIME_PACKAGE_NAME}=={version}"


def load_pinned_runtime_requirement_version(requirements_path: Path) -> str:
    """Return the pinned runtime package version from a requirements file."""
    lines = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    requirement = lines[0]
    expected_prefix = f"{RUNTIME_PACKAGE_NAME}=="
    if not requirement.startswith(expected_prefix):
        raise ValueError(
            f"{requirements_path} must pin {RUNTIME_PACKAGE_NAME} with '=='."
        )
    return requirement.removeprefix(expected_prefix)


def sync_release_versions(project_root: Path) -> str:
    """Sync release artifact versions from pyproject.toml and return the version."""
    version = load_project_version(project_root)
    _sync_galaxy_version(project_root / "galaxy.yml", version)
    _sync_runtime_requirement(project_root / "requirements.txt", version)
    _sync_runtime_requirement(project_root / "meta" / "ee-requirements.txt", version)
    return version


def _sync_galaxy_version(galaxy_path: Path, version: str) -> None:
    content = galaxy_path.read_text()
    updated_content, replacements = re.subn(
        r'^(version:\s*)"[^"]+"$',
        rf'\1"{version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise ValueError(f"Unable to update version in {galaxy_path}.")
    galaxy_path.write_text(updated_content)


def _sync_runtime_requirement(requirements_path: Path, version: str) -> None:
    requirements_path.write_text(f"{format_runtime_requirement(version)}\n")
