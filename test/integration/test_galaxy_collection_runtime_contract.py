"""Smoke tests for the Galaxy collection and Python runtime package contract."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


@dataclass(frozen=True)
class InstalledCollection:
    """Installed Galaxy collection paths and environment."""

    archive_path: Path
    collections_path: Path
    env: dict[str, str]
    remote_tmp: Path
    run_dir: Path


@pytest.fixture(scope="module")
def installed_galaxy_collection(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[InstalledCollection]:
    """Build and install the collection archive into an isolated collection path."""
    root = tmp_path_factory.mktemp("galaxy-runtime-contract")
    build_dir = root / "build"
    collections_path = root / "collections"
    run_dir = root / "run"
    ansible_home = root / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"
    ansible_remote_tmp = ansible_home / "remote-tmp"
    galaxy_cache = root / "galaxy-cache"

    for directory in (
        build_dir,
        collections_path,
        run_dir,
        ansible_local_tmp,
        ansible_remote_tmp,
        galaxy_cache,
    ):
        directory.mkdir(parents=True)

    env = {
        **os.environ,
        "ANSIBLE_COLLECTIONS_PATH": str(collections_path),
        "ANSIBLE_GALAXY_CACHE_DIR": str(galaxy_cache),
        "ANSIBLE_HOME": str(ansible_home),
        "ANSIBLE_LOCAL_TEMP": str(ansible_local_tmp),
    }

    _run(
        [
            _required_executable("ansible-galaxy"),
            "collection",
            "build",
            "--force",
            "--output-path",
            str(build_dir),
            ".",
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
    archive_path = _single_collection_archive(build_dir)

    _run(
        [
            _required_executable("ansible-galaxy"),
            "collection",
            "install",
            "--force",
            "-p",
            str(collections_path),
            str(archive_path),
        ],
        cwd=run_dir,
        env=env,
    )

    yield InstalledCollection(
        archive_path=archive_path,
        collections_path=collections_path,
        env=env,
        remote_tmp=ansible_remote_tmp,
        run_dir=run_dir,
    )


def test_galaxy_archive_excludes_python_runtime_package(
    installed_galaxy_collection: InstalledCollection,
) -> None:
    """Verify the Galaxy archive does not ship the PyPI runtime package."""
    with tarfile.open(installed_galaxy_collection.archive_path) as archive:
        archive_names = archive.getnames()

    assert not any(
        name == "exasol" or name.startswith("exasol/") for name in archive_names
    )


@pytest.mark.parametrize(
    ("module_name", "expected_missing_args"),
    [
        ("exasol_query", "login_user, query"),
        ("exasol_user", "login_user, name"),
    ],
)
def test_galaxy_installed_module_uses_configured_python_runtime(
    installed_galaxy_collection: InstalledCollection,
    module_name: str,
    expected_missing_args: str,
) -> None:
    """Verify installed modules import with the configured runtime interpreter."""
    result = subprocess.run(
        [
            _required_executable("ansible"),
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
            f"ansible_python_interpreter={sys.executable}",
            "-e",
            f"ansible_remote_tmp={installed_galaxy_collection.remote_tmp}",
        ],
        cwd=installed_galaxy_collection.run_dir,
        env=installed_galaxy_collection.env,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert f"missing required arguments: {expected_missing_args}" in output
    assert "No module named 'exasol'" not in output


def _single_collection_archive(build_dir: Path) -> Path:
    archives = list(build_dir.glob("exasol-exasol-*.tar.gz"))
    assert len(archives) == 1
    return archives[0]


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    assert executable is not None
    return executable


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
