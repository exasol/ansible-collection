"""Smoke tests for the Galaxy collection and Python runtime package contract."""

from __future__ import annotations

import subprocess
import tarfile
from test.integration.conftest import InstalledCollectionEnvironment

import pytest


def test_galaxy_archive_excludes_python_runtime_package(
    installed_collection_environment: InstalledCollectionEnvironment,
) -> None:
    """Verify the Galaxy archive does not ship the PyPI runtime package."""
    with tarfile.open(installed_collection_environment.archive_path) as archive:
        archive_names = archive.getnames()

    assert not any(
        name == "exasol" or name.startswith("exasol/") for name in archive_names
    )


@pytest.mark.parametrize(
    ("module_name", "expected_messages"),
    [
        ("exasol_grants", ("missing required arguments: login_user",)),
        ("exasol_query", ("missing required arguments: login_user, query",)),
        ("exasol_user", ("missing required arguments: login_user, name",)),
    ],
)
def test_galaxy_installed_module_uses_configured_python_runtime(
    installed_collection_environment: InstalledCollectionEnvironment,
    module_name: str,
    expected_messages: tuple[str, ...],
) -> None:
    """Verify installed modules import with the configured runtime interpreter."""
    result = subprocess.run(
        [
            "ansible",
            "localhost",
            "-c",
            "local",
            "-i",
            "localhost,",
            "-m",
            f"exasol.exasol.{module_name}",
            "-a",
            "",
            "-e",
            f"ansible_python_interpreter={installed_collection_environment.python_executable}",
            "-e",
            f"ansible_remote_tmp={installed_collection_environment.remote_tmp}",
        ],
        cwd=installed_collection_environment.run_dir,
        env=installed_collection_environment.env,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    for expected_message in expected_messages:
        assert expected_message in output
    assert "No module named 'exasol'" not in output
