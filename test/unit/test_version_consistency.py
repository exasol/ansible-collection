"""Tests for version metadata consistency."""

from __future__ import annotations

import tomllib

import yaml

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


def test_project_and_galaxy_versions_match() -> None:
    """Verify that the package and Ansible Galaxy versions stay aligned."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())

    assert pyproject["project"]["version"] == galaxy["version"]
