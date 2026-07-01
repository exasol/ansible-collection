"""Nox sessions for the Exasol Ansible collection."""

# pylint: disable=wildcard-import,unused-wildcard-import

import shutil
import sys
import tempfile
from pathlib import Path

import nox

from collection_manifest import ignore_collection_manifest_paths

# imports all nox task provided by the toolbox
from exasol.toolbox.nox.tasks import *  # noqa: F403
from noxconfig import PROJECT_CONFIG
from release_version import sync_release_versions

# default actions to be run if nothing is explicitly specified with the -s option
nox.options.sessions = ["format:fix"]

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
COLLECTION_NAMESPACE = "exasol"
COLLECTION_NAME = "exasol"
ANSIBLE_TEST_SOURCE_PATHS = (
    "exasol",
    "tests",
    "tests/integration",
    "tests/integration/targets",
)


def _ignore_collection_build_paths(directory: str, names: list[str]) -> set[str]:
    """Return paths excluded by the Galaxy collection manifest."""
    return ignore_collection_manifest_paths(directory, names)


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

        if any(
            relative_path == allowed_path
            or relative_path.startswith(f"{allowed_path}/")
            or allowed_path.startswith(f"{relative_path}/")
            for allowed_path in ANSIBLE_TEST_SOURCE_PATHS
        ):
            ignored_names.remove(name)

    return ignored_names


def _ansible_env(tmp_path: Path) -> dict[str, str]:
    """Return Ansible environment variables rooted in a writable temp path."""
    ansible_home = tmp_path / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"
    ansible_tmpdir = tmp_path / ".tmp"
    ansible_local_tmp.mkdir(parents=True, exist_ok=True)
    ansible_tmpdir.mkdir(parents=True, exist_ok=True)

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


@nox.session(name="release:sync-version", python=False)
def release_sync_version(session: nox.Session) -> None:
    """Sync versioned release artifacts from pyproject.toml."""
    version = sync_release_versions(PROJECT_ROOT)
    session.log(f"Synchronized release artifact versions to {version}.")
