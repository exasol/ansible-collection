"""Tests for version metadata consistency."""

from __future__ import annotations

import yaml

from noxconfig import PROJECT_CONFIG
from release_version import (
    RUNTIME_PACKAGE_NAME,
    format_runtime_requirement,
    load_pinned_runtime_requirement_version,
    load_project_version,
    sync_release_versions,
)

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


def test_release_artifact_versions_match_project_version() -> None:
    """Verify that all versioned release artifacts stay aligned."""
    project_version = load_project_version(PROJECT_ROOT)
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())
    requirements_version = load_pinned_runtime_requirement_version(
        PROJECT_ROOT / "requirements.txt"
    )
    ee_requirements_version = load_pinned_runtime_requirement_version(
        PROJECT_ROOT / "meta" / "ee-requirements.txt"
    )

    assert project_version == galaxy["version"]
    assert project_version == requirements_version
    assert project_version == ee_requirements_version


def test_runtime_requirements_use_exact_pin() -> None:
    """Verify that runtime requirements do not resolve a newer package release."""
    project_version = load_project_version(PROJECT_ROOT)
    expected_requirement = format_runtime_requirement(project_version)

    assert (
        PROJECT_ROOT / "requirements.txt"
    ).read_text().strip() == expected_requirement
    assert (
        PROJECT_ROOT / "meta" / "ee-requirements.txt"
    ).read_text().strip() == expected_requirement


def test_sync_release_versions_updates_release_artifacts(tmp_path) -> None:
    """Verify that the release sync task rewrites all derived version files."""
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    (tmp_path / "galaxy.yml").write_text(
        'namespace: exasol\nname: exasol\nversion: "0.0.1"\n'
    )
    (tmp_path / "requirements.txt").write_text(f"{RUNTIME_PACKAGE_NAME}==0.0.1\n")
    (tmp_path / "meta").mkdir()
    (tmp_path / "meta" / "ee-requirements.txt").write_text(
        f"{RUNTIME_PACKAGE_NAME}==0.0.1\n"
    )

    version = sync_release_versions(tmp_path)

    assert version == "1.2.3"
    assert 'version: "1.2.3"' in (tmp_path / "galaxy.yml").read_text()
    assert (
        tmp_path / "requirements.txt"
    ).read_text() == f"{RUNTIME_PACKAGE_NAME}==1.2.3\n"
    assert (
        tmp_path / "meta" / "ee-requirements.txt"
    ).read_text() == f"{RUNTIME_PACKAGE_NAME}==1.2.3\n"
