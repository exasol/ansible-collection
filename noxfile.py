"""Nox sessions for the Exasol Ansible collection."""

# pylint: disable=wildcard-import,unused-wildcard-import

import os
import shutil
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import nox
import yaml
from nox.command import CommandFailed

from collection_manifest import ignore_collection_manifest_paths

# imports all nox task provided by the toolbox
from exasol.toolbox.nox.tasks import *  # noqa: F403
from noxconfig import PROJECT_CONFIG

# default actions to be run if nothing is explicitly specified with the -s option
nox.options.sessions = ["format:fix"]

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
OPENFASTTRACE_VERSION = "4.4.0"


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
ANSIBLE_TEST_SOURCE_PATHS = (
    "exasol",
    "galaxy.yml",
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


def _openfasttrace_local_repo(session: nox.Session) -> Path:
    """Return the Maven local repository path used by the OFT wrapper."""
    default_local_repo = Path.home() / ".m2" / "repository"
    if default_local_repo.is_dir():
        return default_local_repo

    local_repo = session.run(
        "mvn",
        "help:evaluate",
        "-Dexpression=settings.localRepository",
        "-q",
        "-DforceStdout",
        silent=True,
    )
    if not local_repo:
        raise RuntimeError(
            "Could not determine Maven local repository path. "
            "Please ensure Maven is installed and configured correctly."
        )
    return Path(local_repo.strip())


def _openfasttrace_jar_file(session: nox.Session) -> Path:
    """Return the OpenFastTrace JAR path, downloading it if needed."""
    local_repo = _openfasttrace_local_repo(session)
    jar_file = (
        local_repo
        / "org"
        / "itsallcode"
        / "openfasttrace"
        / "openfasttrace"
        / OPENFASTTRACE_VERSION
        / f"openfasttrace-{OPENFASTTRACE_VERSION}.jar"
    )

    if not jar_file.is_file():
        session.log(f"Downloading OpenFastTrace {OPENFASTTRACE_VERSION}...")
        session.run(
            "mvn",
            "--batch-mode",
            "org.apache.maven.plugins:maven-dependency-plugin:3.11.0:get",
            f"-Dartifact=org.itsallcode.openfasttrace:openfasttrace:{OPENFASTTRACE_VERSION}",
            "-Dtransitive=false",
        )

    return jar_file


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


@nox.session(name="collection:doc", python=False)
def collection_ansible_doc(session: nox.Session) -> None:
    """Run ansible-doc for all collection modules and fail on documentation issues."""
    output_path = PROJECT_ROOT / ".build_output" / "ansible-doc"
    output_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ansible-collection-doc-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        collection_path = _prepare_ansible_test_collection_layout(tmp_path)
        env = _ansible_env(tmp_path)
        module_names = sorted(
            module_path.stem
            for module_path in (PROJECT_ROOT / "plugins" / "modules").glob("*.py")
            if module_path.stem != "__init__"
        )

        with session.chdir(collection_path):
            for module_name in module_names:
                output_file = output_path / f"{module_name}.txt"
                try:
                    with output_file.open("w", encoding="utf-8") as doc_output:
                        session.run(
                            "ansible-doc",
                            "--type",
                            "module",
                            f"{COLLECTION_NAMESPACE}.{COLLECTION_NAME}.{module_name}",
                            env=env,
                            stdout=doc_output,
                        )
                except CommandFailed:
                    session.log(
                        f"ansible-doc output for {module_name}:\n"
                        f"{output_file.read_text(encoding='utf-8')}"
                    )
                    raise


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

    with tempfile.NamedTemporaryFile(
        mode="w", prefix="ansible_galaxy_", suffix=".cfg"
    ) as config_file:
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


@nox.session(name="requirements:trace", python=False)
def requirements_trace(session: nox.Session) -> None:
    """Run OpenFastTrace locally or in CI without a shell wrapper."""
    jar_file = _openfasttrace_jar_file(session)
    default_args = ["trace", "."]
    # Only include present artifact types until we trace into the code
    default_args = default_args + ["--wanted-artifact-types", "feat,req,scn"]

    trace_args = session.posargs or default_args

    with session.chdir(PROJECT_ROOT):
        session.run("java", "-jar", str(jar_file), *trace_args)
