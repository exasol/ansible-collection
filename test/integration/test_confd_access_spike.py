"""Disposable ITDE evidence for the ConfD access-spike boundaries."""

from __future__ import annotations

import json
import shutil
import ssl
import stat
import subprocess
import sys
import time
from collections.abc import (
    Iterator,
    Sequence,
)
from dataclasses import dataclass
from pathlib import Path
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)
from uuid import uuid4

import pytest
from docker.errors import DockerException
from exasol_integration_test_docker_environment.lib.api import spawn_test_environment
from exasol_integration_test_docker_environment.lib.docker import ContextDockerClient
from exasol_integration_test_docker_environment.lib.models.api_errors import (
    TaskRuntimeError,
)
from exasol_integration_test_docker_environment.lib.test_environment.ports import (
    find_free_ports,
)

_DOCKER_DB_VERSION = "8.29.13"


@dataclass(frozen=True)
class _ConfdItdeEnvironment:
    """Only the disposable connection details needed by the ConfD tests."""

    container_name: str
    ssh_key: Path
    ssh_port: int
    known_hosts: Path


@dataclass(frozen=True)
class _ConfdJsonRpcEnvironment:
    """Only the disposable connection details needed by the JSON-RPC tests."""

    container_name: str
    container_ip: str
    authentication_token: str


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


@pytest.fixture(scope="module")
def confd_json_rpc_environment(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[_ConfdJsonRpcEnvironment]:
    """Start a default ITDE fixture without requesting SSH OS access."""
    _skip_when_docker_is_unavailable()
    root = tmp_path_factory.mktemp("confd-json-rpc-itde")
    environment_name = f"confd-json-rpc-spike-{uuid4().hex[:12]}"
    patch = pytest.MonkeyPatch()
    patch.setenv("HOME", str(root / "home"))
    if sys.platform == "darwin":
        patch.setenv("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    (root / "temporary").mkdir()

    cleanup = None
    try:
        (
            database_port,
            bucketfs_http_port,
            bucketfs_https_port,
            ssh_port,
        ) = find_free_ports(4)
        environment_info, cleanup = spawn_test_environment(
            environment_name=environment_name,
            docker_db_image_version=_DOCKER_DB_VERSION,
            # Avoid shared ITDE defaults; ConfD itself remains unforwarded.
            database_port_forward=database_port,
            bucketfs_port_forward=bucketfs_http_port,
            bucketfs_https_port_forward=bucketfs_https_port,
            ssh_port_forward=ssh_port,
            output_directory=str(root / "output"),
            temporary_base_directory=str(root / "temporary"),
            workers=5,
        )
        container_info = environment_info.database_info.container_info
        assert container_info is not None

        with ContextDockerClient() as docker_client:
            container = docker_client.containers.get(container_info.container_name)
            token_result = container.exec_run(
                ["awk", "/^AuthenticationToken =/ { print $3 }", "/exa/etc/EXAConf"]
            )

        authentication_token = token_result.output.decode("utf-8").strip()
        assert token_result.exit_code == 0
        assert authentication_token
        yield _ConfdJsonRpcEnvironment(
            container_name=container_info.container_name,
            container_ip=container_info.ip_address,
            authentication_token=authentication_token,
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


def _confd_json_rpc_request(
    environment: _ConfdJsonRpcEnvironment,
    token: str,
    payload: dict[str, object],
) -> tuple[int, str]:
    """Execute the agreed read-only ConfD request through the container IP."""
    request = Request(
        f"https://{environment.container_ip}:443/rest",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}"},
        method="POST",
    )
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        with urlopen(
            request,
            timeout=30,
            context=ssl_context,
        ) as response:  # noqa: S310 -- disposable ITDE container IP
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")
    except (TimeoutError, URLError) as error:
        return 0, type(error).__name__


def _confd_json_rpc_db_list(
    environment: _ConfdJsonRpcEnvironment,
    token: str,
) -> tuple[int, str]:
    """Start the read-only job and wait for its result."""
    status, body = _confd_json_rpc_request(
        environment,
        token,
        {
            "method": "job_start",
            "job": "db_list",
            "params": {"params": {}, "dry_run": False, "volatile": False},
        },
    )
    if status != 200:
        return status, body

    job_id = json.loads(body)
    if not isinstance(job_id, str):
        return status, body

    for _ in range(30):
        time.sleep(0.5)
        status, body = _confd_json_rpc_request(
            environment,
            token,
            {"method": "job_result", "params": {"job_id": job_id}},
        )
        if status != 200:
            return status, body
        if json.loads(body).get("result_code") != 5:
            return status, body

    return 0, "ConfD db_list job did not finish within 15 seconds"


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-docker-json-rpc-boundary-evidence~2]
def test_itde_confd_does_not_forward_the_configured_rpc_port(
    confd_json_rpc_environment: _ConfdJsonRpcEnvironment,
) -> None:
    """Record the configured ConfD RPC port and current host port boundary."""
    with ContextDockerClient() as docker_client:
        container = docker_client.containers.get(
            confd_json_rpc_environment.container_name
        )
        result = container.exec_run(
            ["grep", "-E", "^(XMLRPCPort|ExposedPorts)", "/exa/etc/EXAConf"]
        )
        container.reload()

    exaconf = result.output.decode("utf-8")
    port_bindings = container.attrs["NetworkSettings"]["Ports"]

    assert result.exit_code == 0
    assert "XMLRPCPort = 443" in exaconf
    assert "22/tcp" in port_bindings
    assert "443/tcp" not in port_bindings


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-container-ip-json-rpc-evidence~1]
def test_itde_confd_container_ip_runs_authenticated_json_rpc_db_list(
    confd_json_rpc_environment: _ConfdJsonRpcEnvironment,
) -> None:
    """Verify the read-only ConfD JSON request through the container IP."""
    status, body = _confd_json_rpc_db_list(
        confd_json_rpc_environment,
        confd_json_rpc_environment.authentication_token,
    )

    assert status == 200, body
    response = json.loads(body)
    assert response["result_code"] == 0
    assert isinstance(response["result_output"], list)


@pytest.mark.integration
@pytest.mark.slow
# [itest -> dsn~confd-container-ip-json-rpc-evidence~1]
def test_itde_confd_container_ip_rejects_an_unknown_bearer_token(
    confd_json_rpc_environment: _ConfdJsonRpcEnvironment,
) -> None:
    """Verify that rejected container-IP requests do not disclose the token."""
    status, body = _confd_json_rpc_request(
        confd_json_rpc_environment,
        "confd-spike-invalid-token",
        {
            "method": "job_start",
            "job": "db_list",
            "params": {"params": {}, "dry_run": False, "volatile": False},
        },
    )

    assert status in (401, 403)
    assert confd_json_rpc_environment.authentication_token not in body


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
