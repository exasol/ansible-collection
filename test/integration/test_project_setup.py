"""Integration checks for project bootstrap files."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_galaxy_metadata_exists() -> None:
    """Verify that Ansible Galaxy metadata is part of the project."""
    assert (PROJECT_ROOT / "galaxy.yml").is_file()
