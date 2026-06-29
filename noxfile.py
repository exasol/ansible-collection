"""Nox sessions for the Exasol Ansible collection."""

# pylint: disable=wildcard-import,unused-wildcard-import

import fnmatch
from functools import lru_cache
import os
import shutil
import sys
import tempfile
from pathlib import Path

import nox
import yaml  # type: ignore[import-untyped]

# imports all nox task provided by the toolbox
from exasol.toolbox.nox.tasks import *  # noqa: F403
from noxconfig import PROJECT_CONFIG

# default actions to be run if nothing is explicitly specified with the -s option
nox.options.sessions = ["format:fix"]

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


@lru_cache(maxsize=1)
def _collection_metadata() -> dict[str, str]:
    """Return collection metadata from galaxy.yml."""
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())
    return {
        "namespace": galaxy["namespace"],
        "name": galaxy["name"],
        "version": galaxy["version"],
    }


COLLECTION_METADATA = _collection_metadata()
COLLECTION_NAMESPACE = COLLECTION_METADATA["namespace"]
COLLECTION_NAME = COLLECTION_METADATA["name"]
COLLECTION_VERSION = COLLECTION_METADATA["version"]


def _collection_build_ignore_patterns() -> tuple[str, ...]:
    """Return collection build ignore patterns from galaxy.yml."""
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())
    return tuple(galaxy.get("build_ignore", ()))


def _ignore_collection_build_paths(directory: str, names: list[str]) -> set[str]:
    """Return paths ignored by the collection build configuration."""
    ignored_names = set()
    patterns = _collection_build_ignore_patterns()
    directory_path = Path(directory)

    for name in names:
        path = directory_path / name
        try:
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative_path = name

        if any(
            fnmatch.fnmatch(name, pattern)
            or fnmatch.fnmatch(relative_path, pattern)
            or relative_path.startswith(f"{pattern.rstrip('/')}/")
            for pattern in patterns
        ):
            ignored_names.add(name)

    return ignored_names


def _ignore_ansible_test_source_paths(directory: str, names: list[str]) -> set[str]:
    """Return paths ignored when preparing the ansible-test source layout.

    The Galaxy archive must ignore the top-level exasol/ package because the
    runtime is provided by the PyPI package. The temporary ansible-test source
    layout is different: sanity imports module files before that PyPI runtime is
    installed in its isolated venvs, so the source runtime package must stay
    available there.
    """
    ignored_names = _ignore_collection_build_paths(directory, names)
    directory_path = Path(directory)

    for name in tuple(ignored_names):
        path = directory_path / name
        try:
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            continue

        # ansible-test sanity imports modules from an isolated venv before the
        # PyPI runtime package is installed. Keep the source runtime package in
        # this temporary test layout; galaxy.yml still excludes it from archives.
        if relative_path == "exasol" or relative_path.startswith("exasol/"):
            ignored_names.remove(name)

    return ignored_names


def _ansible_env(tmp_path: Path) -> dict[str, str]:
    """Return Ansible environment variables rooted in a writable temp path."""
    ansible_home = tmp_path / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"
    ansible_local_tmp.mkdir(parents=True, exist_ok=True)

    return {
        "ANSIBLE_HOME": str(ansible_home),
        "ANSIBLE_LOCAL_TEMP": str(ansible_local_tmp),
        "HOME": str(tmp_path),
    }


def _skip_if_ansible_test_does_not_support_python(session: nox.Session) -> None:
    """Skip ansible-test sessions on Python versions it cannot execute with."""
    current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    if current_python not in PROJECT_CONFIG.ansible_test_python_versions:
        supported_versions = ", ".join(PROJECT_CONFIG.ansible_test_python_versions)
        session.skip(
            "ansible-test supports Python "
            f"{supported_versions}; current interpreter is {current_python}."
        )


def _prepare_ansible_test_collection_layout(tmp_path: Path) -> Path:
    """Copy this checkout into the collection layout expected by ansible-test."""
    collection_path = (
        tmp_path / "ansible_collections" / COLLECTION_NAMESPACE / COLLECTION_NAME
    )
    collection_path.parent.mkdir(parents=True)

    shutil.copytree(
        PROJECT_ROOT,
        collection_path,
        ignore=_ignore_ansible_test_source_paths,
    )

    return collection_path


@nox.session(name="collection:build", python=False)
def collection_build(session: nox.Session) -> None:
    """Build the Ansible collection archive."""
    # Keep Galaxy archives separate from Python artifacts checked by package:check.
    output_path = PROJECT_ROOT / ".build_output" / "collections"
    output_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ansible-collection-build-") as tmp_dir:
        with session.chdir(PROJECT_ROOT):
            session.run(
                "ansible-galaxy",
                "collection",
                "build",
                "--force",
                "--output-path",
                str(output_path),
                ".",
                env=_ansible_env(Path(tmp_dir)),
            )


@nox.session(name="collection:sanity", python=False)
def collection_sanity(session: nox.Session) -> None:
    """Run ansible-test sanity in a temporary collection namespace layout."""
    _skip_if_ansible_test_does_not_support_python(session)

    with tempfile.TemporaryDirectory(prefix="ansible-collection-sanity-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        collection_path = _prepare_ansible_test_collection_layout(tmp_path)
        env = _ansible_env(tmp_path)

        with session.chdir(collection_path):
            session.run(
                "ansible-test",
                "sanity",
                "--python-interpreter",
                sys.executable,
                env=env,
            )


@nox.session(name="collection:integration", python=False)
def collection_integration(session: nox.Session) -> None:
    """Run ansible-test integration in a temporary collection namespace layout."""
    _skip_if_ansible_test_does_not_support_python(session)

    with tempfile.TemporaryDirectory(
        prefix="ansible-collection-integration-"
    ) as tmp_dir:
        tmp_path = Path(tmp_dir)
        collection_path = _prepare_ansible_test_collection_layout(tmp_path)

        with session.chdir(collection_path):
            session.run(
                "ansible-test",
                "integration",
                "--python-interpreter",
                sys.executable,
                *session.posargs,
                env=_ansible_env(tmp_path),
            )

@nox.session(name="collection:publish", python=False)
def collection_publish(session: nox.Session) -> None:
    """Publish the Ansible collection archive to Ansible Galaxy.
    This requires an Ansible Galaxy API token in ANSIBLE_GALAXY_TOKEN.
    """
    collection_archive = (
        PROJECT_ROOT
        / ".build_output"
        / "collections"
        / f"{COLLECTION_NAMESPACE}-{COLLECTION_NAME}-{COLLECTION_VERSION}.tar.gz"
    )

    with tempfile.NamedTemporaryFile(mode="w", prefix="ansible_galaxy_", suffix=".cfg") as config_file:
        token = os.environ.get("ANSIBLE_GALAXY_TOKEN")
        if not token:
            raise RuntimeError("Set environment variable ANSIBLE_GALAXY_TOKEN.")

        # Configuration file is required by ansible-galaxy to read the token from the environment variable.
        config_file.write("""
[galaxy]
server_list = galaxy

[galaxy_server.galaxy]
url = https://galaxy.ansible.com/
""")
        config_file.flush()

        with session.chdir(PROJECT_ROOT):
            session.run(
                "ansible-galaxy",
                "collection",
                "publish",
                str(collection_archive),
                "-vvvvvvvv",
                "--server",
                "galaxy",
                env={
                    "ANSIBLE_CONFIG": str(config_file.name),
                    "ANSIBLE_GALAXY_SERVER_GALAXY_TOKEN": token,
                },
            )
