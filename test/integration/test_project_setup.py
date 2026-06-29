"""Integration checks for project bootstrap files."""

from __future__ import annotations

import yaml

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


def test_galaxy_metadata_defines_collection() -> None:
    """Verify that Ansible Galaxy metadata defines the collection identity."""
    galaxy_path = PROJECT_ROOT / "galaxy.yml"

    assert galaxy_path.is_file()

    galaxy = yaml.safe_load(galaxy_path.read_text())

    assert galaxy["namespace"] == "exasol"
    assert galaxy["name"] == "exasol"
    assert galaxy["readme"] == "README.md"
    assert galaxy["authors"]
    assert galaxy["repository"] == "https://github.com/exasol/ansible-collection"
    assert {"exasol", "database", "analytics", "datawarehouse"}.issubset(galaxy["tags"])
    assert galaxy.get("license") or galaxy.get("license_file")

    if license_file := galaxy.get("license_file"):
        assert (PROJECT_ROOT / license_file).is_file()


def test_standard_collection_directories_exist() -> None:
    """Verify that the repository exposes the standard collection skeleton."""
    expected_directories = {
        "plugins/modules",
        "plugins/doc_fragments",
    }

    for directory in expected_directories:
        assert (PROJECT_ROOT / directory).is_dir()


def test_collection_runtime_metadata_exists() -> None:
    """Verify that collection runtime metadata is present."""
    runtime_path = PROJECT_ROOT / "meta" / "runtime.yml"

    assert runtime_path.is_file()

    runtime = yaml.safe_load(runtime_path.read_text())

    assert runtime["requires_ansible"]


def test_collection_execution_environment_metadata_exists() -> None:
    """Verify that ansible-builder collection dependency metadata is present."""
    metadata_path = PROJECT_ROOT / "meta" / "execution-environment.yml"
    python_requirements_path = PROJECT_ROOT / "meta" / "ee-requirements.txt"
    system_requirements_path = PROJECT_ROOT / "meta" / "ee-bindep.txt"

    assert metadata_path.is_file()
    assert python_requirements_path.is_file()
    assert system_requirements_path.is_file()

    metadata = yaml.safe_load(metadata_path.read_text())

    assert metadata["dependencies"]["python"] == "meta/ee-requirements.txt"
    assert metadata["dependencies"]["system"] == "meta/ee-bindep.txt"
    assert "exasol-ansible-modules" in python_requirements_path.read_text().splitlines()
