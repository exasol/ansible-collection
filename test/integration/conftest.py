"""Shared fixtures for pytest-driven Ansible integration tests."""

from __future__ import annotations

import os
import shutil
import site
import ssl
import socket
import subprocess
import sys
from hashlib import sha256
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from collection_manifest import ignore_collection_manifest_paths
from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
INTEGRATION_ROOT = Path(__file__).resolve().parent
COLLECTION_NAMESPACE = "exasol"
COLLECTION_NAME = "exasol"

if str(INTEGRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_ROOT))

from acceptance_common.acceptance_test_common import cleanup_database_objects


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


@dataclass(frozen=True)
class InstalledCollectionEnvironment:
    """Built collection plus isolated runtime installation for E2E tests."""

    root: Path
    archive_path: Path
    collections_path: Path
    run_dir: Path
    remote_tmp: Path
    env: dict[str, str]
    venv_dir: Path
    python_executable: Path


def _ignore_collection_build_paths(directory: str, names: list[str]) -> set[str]:
    return ignore_collection_manifest_paths(directory, names)


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
    ansible_remote_tmp = ansible_home / "remote-tmp"

    project_dir.mkdir(parents=True)
    env_dir.mkdir()
    ansible_local_tmp.mkdir(parents=True)
    ansible_remote_tmp.mkdir(parents=True)

    inventory_path = private_data_dir / "inventory"
    inventory_path.write_text(
        "localhost ansible_connection=local "
        f"ansible_remote_tmp={ansible_remote_tmp}\n"
    )

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
        "ANSIBLE_REMOTE_TEMP": str(ansible_remote_tmp),
        "ANSIBLE_REMOTE_TMP": str(ansible_remote_tmp),
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


@pytest.fixture(scope="module")
def installed_collection_environment(
    tmp_path_factory: pytest.TempPathFactory,
) -> InstalledCollectionEnvironment:
    """Build and install the collection plus runtime into isolated temp paths."""
    root = tmp_path_factory.mktemp("installed-collection-environment")
    build_dir = root / "build"
    wheel_dir = root / "wheel"
    collections_path = root / "collections"
    run_dir = root / "run"
    ansible_home = root / ".ansible"
    ansible_local_tmp = ansible_home / "tmp"
    ansible_remote_tmp = ansible_home / "remote-tmp"
    galaxy_cache = root / "galaxy-cache"
    venv_dir = root / "runtime-venv"

    for directory in (
        build_dir,
        wheel_dir,
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

    _run_command(
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

    _run_command(
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

    _run_command(
        [
            _required_executable("poetry"),
            "build",
            "--format",
            "wheel",
            "--output",
            str(wheel_dir),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
    runtime_wheel = _single_runtime_wheel(wheel_dir)

    _run_command(
        [
            sys.executable,
            "-m",
            "venv",
            "--system-site-packages",
            str(venv_dir),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
    python_executable = _venv_python(venv_dir)
    _link_current_site_packages(venv_dir)
    _run_command(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(runtime_wheel),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )

    return InstalledCollectionEnvironment(
        root=root,
        archive_path=archive_path,
        collections_path=collections_path,
        run_dir=run_dir,
        remote_tmp=ansible_remote_tmp,
        env=env,
        venv_dir=venv_dir,
        python_executable=python_executable,
    )


@pytest.fixture
def exasol_connection(
    backend_aware_database_params: dict[str, Any],
) -> ExasolConnection:
    """Return backend connection details normalized for Ansible modules."""
    dsn = backend_aware_database_params["dsn"]
    host, fingerprint, port = _parse_pyexasol_dsn(dsn)
    websocket_sslopt = backend_aware_database_params.get("websocket_sslopt") or {}
    validate_certs = websocket_sslopt.get("cert_reqs") != ssl.CERT_NONE
    effective_fingerprint = _backend_certificate_fingerprint(
        backend_aware_database_params,
        dsn_fingerprint=fingerprint,
        host=host,
        port=port,
        validate_certs=validate_certs,
    )

    return ExasolConnection(
        host=host,
        port=port,
        user=backend_aware_database_params.get("user")
        or backend_aware_database_params["username"],
        password=backend_aware_database_params["password"],
        validate_certs=validate_certs,
        certificate_fingerprint=effective_fingerprint,
    )


@pytest.fixture
def exasol_login_vars(exasol_connection: ExasolConnection) -> dict[str, object]:
    """Return backend connection details using collection module argument names."""
    return exasol_connection.login_vars


@pytest.fixture(autouse=True)
def cleanup_exasol_objects_before_test(
    request: pytest.FixtureRequest,
) -> None:
    """Delete non-system Exasol objects before each DB-backed integration test."""
    if "exasol_login_vars" not in request.fixturenames:
        return
    cleanup_database_objects(request.getfixturevalue("exasol_login_vars"))


def _parse_pyexasol_dsn(dsn: str) -> tuple[str, str | None, int]:
    address, port_text = dsn.rsplit(":", 1)
    if "/" in address:
        host, fingerprint = address.split("/", 1)
    else:
        host, fingerprint = address, None
    return host, fingerprint, int(port_text)


def _backend_certificate_fingerprint(
    backend_aware_database_params: dict[str, Any],
    *,
    dsn_fingerprint: str | None,
    host: str,
    port: int,
    validate_certs: bool,
) -> str | None:
    if dsn_fingerprint:
        return dsn_fingerprint

    configured_fingerprint = backend_aware_database_params.get(
        "certificate_fingerprint"
    ) or os.environ.get("EXASOL_CERTIFICATE_FINGERPRINT")
    if configured_fingerprint:
        fingerprint = str(configured_fingerprint).strip()
        if fingerprint:
            return fingerprint

    if validate_certs:
        return None

    return _certificate_fingerprint_for_endpoint(host, port)


def _certificate_fingerprint_for_endpoint(host: str, port: int) -> str:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port)) as tcp_socket:
        with context.wrap_socket(tcp_socket, server_hostname=host) as tls_socket:
            certificate = tls_socket.getpeercert(binary_form=True)
    return sha256(certificate).hexdigest().upper()


def _required_executable(name: str) -> str:
    executable = shutil.which(name)
    assert executable is not None
    return executable


def _run_command(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _single_collection_archive(build_dir: Path) -> Path:
    archives = list(build_dir.glob("exasol-exasol-*.tar.gz"))
    assert len(archives) == 1
    return archives[0]


def _single_runtime_wheel(wheel_dir: Path) -> Path:
    wheels = list(wheel_dir.glob("exasol_ansible_modules-*.whl"))
    assert len(wheels) == 1
    return wheels[0]


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _link_current_site_packages(venv_dir: Path) -> None:
    venv_site_packages = _venv_site_packages(venv_dir)
    linked_paths = [
        Path(path)
        for path in dict.fromkeys(
            [*site.getsitepackages(), site.getusersitepackages(), *sys.path]
        )
        if "site-packages" in path
    ]
    pth_file = venv_site_packages / "ansible_collection_test_deps.pth"
    pth_file.write_text(
        "".join(f"{path}\n" for path in linked_paths if path.is_dir()),
        encoding="utf-8",
    )


def _venv_site_packages(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Lib" / "site-packages"
    return (
        venv_dir
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
