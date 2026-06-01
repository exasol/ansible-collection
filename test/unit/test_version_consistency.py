"""Tests for version metadata consistency."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_project_and_galaxy_versions_match() -> None:
    """Verify that the package and Ansible Galaxy versions stay aligned."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())

    assert pyproject["project"]["version"] == galaxy["version"]
