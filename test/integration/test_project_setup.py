"""Integration checks for project bootstrap files."""

from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_galaxy_metadata_defines_collection() -> None:
    """Verify that Ansible Galaxy metadata defines the collection identity."""
    galaxy_path = PROJECT_ROOT / "galaxy.yml"

    assert galaxy_path.is_file()

    galaxy = yaml.safe_load(galaxy_path.read_text())

    assert galaxy["namespace"] == "exasol"
    assert galaxy["name"] == "ansible_collection"
    assert galaxy["readme"] == "README.md"
    assert galaxy["authors"]
    assert galaxy["repository"] == "https://github.com/exasol/ansible-collection"
    assert {"exasol", "database", "installer"}.issubset(galaxy["tags"])
    assert galaxy.get("license") or galaxy.get("license_file")

    if license_file := galaxy.get("license_file"):
        assert (PROJECT_ROOT / license_file).is_file()


def test_collection_runtime_metadata_exists() -> None:
    """Verify that collection runtime metadata is present."""
    runtime_path = PROJECT_ROOT / "meta" / "runtime.yml"

    assert runtime_path.is_file()

    runtime = yaml.safe_load(runtime_path.read_text())

    assert runtime["requires_ansible"]
