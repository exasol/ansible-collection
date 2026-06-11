"""Exasol backend tests for the exasol_query Ansible module."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from exasol.ansible.playbook import Playbook
from exasol.ansible.runner import Runner

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()
PLAYBOOK_RESOURCE = (
    PROJECT_ROOT
    / "test"
    / "integration"
    / "exasol_query"
    / "exasol_query_playbook.yml"
)


@pytest.mark.integration
@pytest.mark.slow
def test_exasol_query_module_executes_against_exasol(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the public exasol_query module against Exasol backend."""
    schema_name = f"ANSIBLE_QUERY_{uuid.uuid4().hex.upper()}"
    invalid_password = f"invalid-{uuid.uuid4().hex}"
    playbook = _write_playbook(ansible_runner_workspace.project_dir)

    runner = Runner(
        repositories=(),
        work_dir=ansible_runner_workspace.private_data_dir,
    )

    facts = runner.run(
        Playbook(
            playbook.name,
            {
                **exasol_login_vars,
                "ansible_python_interpreter": sys.executable,
                "test_schema": schema_name,
                "invalid_login_password": invalid_password,
            },
        ),
        retrieve_facts_from="localhost",
    )

    assert facts["exasol_query_backend_probe"] == {
        "schema": schema_name,
        "metadata_version_available": True,
        "single_select": "1",
        "batch_row_count": "1",
        "positional_value": "42",
        "named_value": "7",
        "check_mode_select": "1",
        "check_mode_schema_count": "0",
        "bad_credentials_sanitized": True,
    }


def _write_playbook(project_dir: Path) -> Path:
    playbook = project_dir / "exasol_query_backend.yml"
    playbook.write_text(
        PLAYBOOK_RESOURCE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return playbook
