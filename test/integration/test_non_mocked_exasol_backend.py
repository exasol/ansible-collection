"""Non-mocked Exasol backend tests executed through the Ansible runner wrapper."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from exasol.ansible.playbook import Playbook
from exasol.ansible.runner import Runner

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
INTEGRATION_RESOURCES = PROJECT_ROOT / "test" / "integration" / "resources"
PROBE_SCRIPT_RESOURCE = INTEGRATION_RESOURCES / "non_mocked_exasol_backend_probe.py"
PROBE_PLAYBOOK_RESOURCE = INTEGRATION_RESOURCES / "non_mocked_exasol_backend_playbook.yml"


@pytest.mark.integration
@pytest.mark.slow
def test_ansible_runner_wrapper_executes_playbook_against_non_mocked_exasol(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify runner-wrapper execution against a non-mocked Exasol backend."""
    schema_name = f"ANSIBLE_COLLECTION_ITEST_{uuid.uuid4().hex.upper()}"
    project_dir = ansible_runner_workspace.project_dir
    params_file = _write_probe_params(project_dir, exasol_login_vars, schema_name)
    _write_probe_script(project_dir)
    playbook = _write_probe_playbook(project_dir)

    runner = Runner(
        repositories=(),
        work_dir=ansible_runner_workspace.private_data_dir,
    )

    facts = runner.run(
        Playbook(
            playbook.name,
            {
                **exasol_login_vars,
                "exasol_probe_params_file": str(params_file),
                "python_executable": sys.executable,
            },
        ),
        retrieve_facts_from="localhost",
    )

    assert facts["exasol_backend_probe"] == {
        "schema": schema_name,
        "row_count": 1,
        "note": "runner-wrapper",
        "selected_value": 42,
    }


def _write_probe_params(
    project_dir: Path,
    login_vars: dict[str, object],
    schema_name: str,
) -> Path:
    params_file = project_dir / "non_mocked_exasol_backend_params.json"
    params = {
        **login_vars,
        "test_schema": schema_name,
    }
    params_file.write_text(json.dumps(params))
    params_file.chmod(0o600)
    return params_file


def _write_probe_playbook(project_dir: Path) -> Path:
    playbook = project_dir / "non_mocked_exasol_backend.yml"
    playbook.write_text(
        PROBE_PLAYBOOK_RESOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return playbook


def _write_probe_script(project_dir: Path) -> Path:
    script = project_dir / "non_mocked_exasol_backend_probe.py"
    script.write_text(
        PROBE_SCRIPT_RESOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return script
