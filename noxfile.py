"""Nox sessions for the Exasol Ansible collection."""

# pylint: disable=wildcard-import,unused-wildcard-import

import fnmatch
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
COLLECTION_NAMESPACE = "exasol"
COLLECTION_NAME = "exasol"


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


def _ansible_env(tmp_path: Path) -> dict[str, str]:
    """Return Ansible environment variables rooted in a writable temp path."""
    ansible_home = tmp_path / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"
    ansible_local_tmp.mkdir(parents=True, exist_ok=True)

    return {
        "ANSIBLE_HOME": str(ansible_home),
        "ANSIBLE_LOCAL_TEMP": str(ansible_local_tmp),
    }


def _prepare_ansible_test_collection_layout(tmp_path: Path) -> Path:
    """Copy this checkout into the collection layout expected by ansible-test."""
    collection_path = (
        tmp_path / "ansible_collections" / COLLECTION_NAMESPACE / COLLECTION_NAME
    )
    collection_path.parent.mkdir(parents=True)

    shutil.copytree(
        PROJECT_ROOT,
        collection_path,
        ignore=_ignore_collection_build_paths,
    )

    return collection_path


@nox.session(name="collection:build", python=False)
def collection_build(session: nox.Session) -> None:
    """Build the Ansible collection archive."""
    (PROJECT_ROOT / "dist").mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ansible-collection-build-") as tmp_dir:
        with session.chdir(PROJECT_ROOT):
            session.run(
                "ansible-galaxy",
                "collection",
                "build",
                "--force",
                "--output-path",
                "dist",
                ".",
                env=_ansible_env(Path(tmp_dir)),
            )


@nox.session(name="collection:sanity", python=False)
def collection_sanity(session: nox.Session) -> None:
    """Run ansible-test sanity in a temporary collection namespace layout."""
    with tempfile.TemporaryDirectory(prefix="ansible-collection-sanity-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        collection_path = _prepare_ansible_test_collection_layout(tmp_path)

        with session.chdir(collection_path):
            session.run(
                "ansible-test",
                "sanity",
                "--python-interpreter",
                sys.executable,
                env=_ansible_env(tmp_path),
            )
