"""Shared fixtures for pytest-driven Ansible integration tests."""

from __future__ import annotations

import fnmatch
import os
import shutil
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
INTEGRATION_ROOT = Path(__file__).resolve().parent
COLLECTION_NAMESPACE = "exasol"
COLLECTION_NAME = "exasol"

if str(INTEGRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_ROOT))


@dataclass(frozen=True)
class AnsibleRunnerWorkspace:
    """Temporary Ansible runner workspace rooted at a local collection checkout."""

    root: Path
    private_data_dir: Path
    project_dir: Path
    collection_path: Path
    envvars: dict[str, str]
    inventory: str


@dataclass(frozen=True)
class ExasolConnection:
    """Normalized Exasol connection details for Ansible module arguments."""

    host: str
    port: int
    user: str
    password: str
    validate_certs: bool
    certificate_fingerprint: str | None = None

    @property
    def login_vars(self) -> dict[str, object]:
        result: dict[str, object] = {
            "login_host": self.host,
            "login_port": self.port,
            "login_user": self.user,
            "login_password": self.password,
            "validate_certs": self.validate_certs,
        }
        if self.certificate_fingerprint:
            result["certificate_fingerprint"] = self.certificate_fingerprint
        return result


def _collection_build_ignore_patterns() -> tuple[str, ...]:
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text())
    return tuple(galaxy.get("build_ignore", ()))


def _ignore_collection_build_paths(directory: str, names: list[str]) -> set[str]:
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


def _prepare_collection_layout(root: Path) -> Path:
    collection_path = (
        root / "ansible_collections" / COLLECTION_NAMESPACE / COLLECTION_NAME
    )
    collection_path.parent.mkdir(parents=True)

    shutil.copytree(
        PROJECT_ROOT,
        collection_path,
        ignore=_ignore_collection_build_paths,
    )

    return collection_path


@pytest.fixture
def ansible_runner_workspace(tmp_path: Path) -> AnsibleRunnerWorkspace:
    """Create an isolated ansible-runner workspace for local collection tests."""
    collection_root = tmp_path / "collections"
    collection_path = _prepare_collection_layout(collection_root)
    private_data_dir = tmp_path / "runner"
    project_dir = private_data_dir / "project"
    env_dir = private_data_dir / "env"
    ansible_home = tmp_path / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"

    project_dir.mkdir(parents=True)
    env_dir.mkdir()
    ansible_local_tmp.mkdir(parents=True)

    inventory_path = private_data_dir / "inventory"
    inventory_path.write_text("localhost ansible_connection=local\n")

    preserved_env_names = {
        "LANG",
        "LC_ALL",
        "PATH",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYENV_VERSION",
        "VIRTUAL_ENV",
    }
    envvars = {
        **{
            name: value
            for name, value in os.environ.items()
            if name in preserved_env_names or name.startswith("PYTHON")
        },
        "ANSIBLE_COLLECTIONS_PATH": str(collection_root),
        "ANSIBLE_HOME": str(ansible_home),
        "ANSIBLE_LOCAL_TEMP": str(ansible_local_tmp),
    }
    (env_dir / "envvars").write_text(yaml.safe_dump(envvars))

    return AnsibleRunnerWorkspace(
        root=tmp_path,
        private_data_dir=private_data_dir,
        project_dir=project_dir,
        collection_path=collection_path,
        envvars=envvars,
        inventory=str(inventory_path),
    )


@pytest.fixture
def exasol_connection(
    backend_aware_database_params: dict[str, Any],
) -> ExasolConnection:
    """Return backend connection details normalized for Ansible modules."""
    dsn = backend_aware_database_params["dsn"]
    host, fingerprint, port = _parse_pyexasol_dsn(dsn)
    websocket_sslopt = backend_aware_database_params.get("websocket_sslopt") or {}

    return ExasolConnection(
        host=host,
        port=port,
        user=backend_aware_database_params.get("user")
        or backend_aware_database_params["username"],
        password=backend_aware_database_params["password"],
        validate_certs=websocket_sslopt.get("cert_reqs") != ssl.CERT_NONE,
        certificate_fingerprint=fingerprint,
    )


@pytest.fixture
def exasol_login_vars(exasol_connection: ExasolConnection) -> dict[str, object]:
    """Return backend connection details using collection module argument names."""
    return exasol_connection.login_vars


def _parse_pyexasol_dsn(dsn: str) -> tuple[str, str | None, int]:
    address, port_text = dsn.rsplit(":", 1)
    if "/" in address:
        host, fingerprint = address.split("/", 1)
    else:
        host, fingerprint = address, None
    return host, fingerprint, int(port_text)
