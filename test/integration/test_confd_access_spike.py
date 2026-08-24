"""Disposable ITDE evidence for the ConfD access-spike boundaries."""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from collections.abc import (
    Iterator,
    Sequence,
)
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from docker.errors import DockerException
from exasol_integration_test_docker_environment.lib.api import spawn_test_environment
from exasol_integration_test_docker_environment.lib.docker import ContextDockerClient
from exasol_integration_test_docker_environment.lib.models.api_errors import (
    TaskRuntimeError,
)


@dataclass(frozen=True)
class _ConfdItdeEnvironment:
    """Only the disposable connection details needed by the ConfD tests."""

    container_name: str
    ssh_key: Path
    ssh_port: int
    known_hosts: Path


@pytest.fixture(scope="module")
def confd_itde_environment(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[_ConfdItdeEnvironment]:
    """Start one disposable Docker-DB fixture with ITDE-managed cleanup."""
    _skip_when_docker_is_unavailable()
    root = tmp_path_factory.mktemp("confd-itde")
    environment_name = f"confd-spike-{uuid4().hex[:12]}"
    patch = pytest.MonkeyPatch()
    patch.setenv("HOME", str(root / "home"))
    if sys.platform == "darwin":
        patch.setenv("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    (root / "temporary").mkdir()

    cleanup = None
    try:
        try:
            environment_info, cleanup = spawn_test_environment(
                environment_name=environment_name,
                db_os_access="SSH",
                output_directory=str(root / "output"),
                temporary_base_directory=str(root / "temporary"),
                workers=5,
            )
        except TaskRuntimeError as error:
            # Temporary until ITDE #673 is resolved; follow-up ticket #143 will restore
            # failure behavior: https://github.com/exasol/ansible-collection/issues/143
            pytest.skip(
                "SSH-enabled ITDE fixture is unavailable pending the ITDE "
                f"readiness blocker: {type(error).__name__}"
            )
        database_info = environment_info.database_info
        container_info = database_info.container_info
        ssh_info = database_info.ssh_info
        forwarded_ports = database_info.forwarded_ports
        assert container_info is not None
        assert ssh_info is not None
        assert forwarded_ports is not None
        assert forwarded_ports.ssh is not None

        yield _ConfdItdeEnvironment(
            container_name=container_info.container_name,
            ssh_key=Path(ssh_info.key_file),
            ssh_port=forwarded_ports.ssh,
            known_hosts=root / "known_hosts",
        )
    finally:
        if cleanup is not None:
            cleanup()
        patch.undo()


def _skip_when_docker_is_unavailable() -> None:
    try:
        with ContextDockerClient() as docker_client:
            docker_client.ping()
    except DockerException as error:
        pytest.skip(f"ITDE Docker prerequisite is unavailable: {type(error).__name__}")


def _ssh(
    environment: _ConfdItdeEnvironment,
    remote_command: Sequence[str],
    *,
    user: str = "root",
) -> subprocess.CompletedProcess[str]:
    ssh = shutil.which("ssh")
    if ssh is None:
        pytest.skip("ITDE SSH prerequisite is unavailable: ssh executable not found")
    return subprocess.run(
        [
            ssh,
            "-i",
            str(environment.ssh_key),
            "-p",
            str(environment.ssh_port),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectionAttempts=1",
            "-o",
            "ConnectTimeout=15",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={environment.known_hosts}",
            f"{user}@127.0.0.1",
            *remote_command,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-docker-json-rpc-boundary-evidence~1]
def test_itde_confd_exposes_ssh_but_not_a_json_rpc_endpoint(
    confd_itde_environment: _ConfdItdeEnvironment,
) -> None:
    """Verify the image's XML-RPC-only configuration and host port boundary."""
    with ContextDockerClient() as docker_client:
        container = docker_client.containers.get(confd_itde_environment.container_name)
        result = container.exec_run(
            ["grep", "-E", "^(XMLRPCPort|ExposedPorts)", "/exa/etc/EXAConf"]
        )
        container.reload()

    exaconf = result.output.decode("utf-8")
    port_bindings = container.attrs["NetworkSettings"]["Ports"]

    assert result.exit_code == 0
    assert "XMLRPCPort = 443" in exaconf
    assert "JSONRPC" not in exaconf
    assert "22/tcp" in port_bindings
    assert "443/tcp" not in port_bindings


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-client-ssh-read-only-evidence~1]
def test_itde_confd_client_db_list_runs_over_ssh(
    confd_itde_environment: _ConfdItdeEnvironment,
) -> None:
    """Verify the agreed read-only ConfD command and temporary key protection."""
    assert stat.S_IMODE(confd_itde_environment.ssh_key.stat().st_mode) == 0o600

    result = _ssh(confd_itde_environment, ("confd_client", "db_list", "-j"))

    assert result.returncode == 0, result.stderr
    databases = json.loads(result.stdout)
    assert isinstance(databases, list)
    assert databases


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-client-ssh-read-only-evidence~1]
def test_itde_confd_ssh_rejects_an_unknown_login_without_key_material(
    confd_itde_environment: _ConfdItdeEnvironment,
) -> None:
    """Verify an SSH authentication failure does not disclose private-key data."""
    result = _ssh(
        confd_itde_environment,
        ("confd_client", "db_list", "-j"),
        user="confd-spike-denied",
    )
    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "BEGIN OPENSSH PRIVATE KEY" not in output
    assert "BEGIN RSA PRIVATE KEY" not in output
    assert str(confd_itde_environment.ssh_key) not in output
