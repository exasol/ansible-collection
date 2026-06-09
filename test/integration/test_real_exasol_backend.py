"""Real Exasol backend tests executed through the Ansible runner wrapper."""

from __future__ import annotations

import json
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Any

import pytest
from exasol.ansible.playbook import Playbook
from exasol.ansible.runner import Runner


@pytest.mark.integration
@pytest.mark.slow
def test_ansible_runner_wrapper_executes_playbook_against_real_exasol(
    ansible_runner_workspace: Any,
    exasol_login_vars: dict[str, object],
) -> None:
    """Verify the runner wrapper can execute collection code against Exasol."""
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
    params_file = project_dir / "real_exasol_backend_params.json"
    params = {
        **login_vars,
        "test_schema": schema_name,
    }
    params_file.write_text(json.dumps(params))
    params_file.chmod(0o600)
    return params_file


def _write_probe_playbook(project_dir: Path) -> Path:
    playbook = project_dir / "real_exasol_backend.yml"
    playbook.write_text(textwrap.dedent("""\
            ---
            - hosts: localhost
              gather_facts: false
              collections:
                - exasol.exasol
              tasks:
                - name: Setup Exasol test environment
                  import_role:
                    name: exasol.exasol.setup_exasol
                  vars:
                    exasol_host: "{{ login_host }}"
                    exasol_port: "{{ login_port }}"
                    exasol_user: "{{ login_user }}"
                    exasol_password: "{{ login_password }}"
                    exasol_validate_certs: "{{ validate_certs }}"
                    exasol_certificate_fingerprint: >-
                      {{ certificate_fingerprint | default('') }}

                - name: Execute real Exasol backend probe
                  ansible.builtin.command:
                    cmd: >-
                      {{ python_executable }}
                      {{ playbook_dir }}/real_exasol_backend_probe.py
                      {{ exasol_probe_params_file }}
                  register: exasol_backend_probe_command
                  changed_when: false

                - name: Store real Exasol backend probe result
                  ansible.builtin.set_fact:
                    exasol_backend_probe: >-
                      {{ exasol_backend_probe_command.stdout | from_json }}
                    cacheable: true
            """))
    return playbook


def _write_probe_script(project_dir: Path) -> Path:
    script = project_dir / "real_exasol_backend_probe.py"
    script.write_text(textwrap.dedent("""\
            from __future__ import annotations

            import json
            import sys
            from pathlib import Path

            import pyexasol
            from exasol.ansible_modules.exasol_query import (
                build_exasol_connect_kwargs,
                to_json_safe,
            )
            from exasol.ansible_modules.exasol_user import quote_identifier


            def main(params_file: str) -> None:
                params = json.loads(Path(params_file).read_text())
                schema_name = params.pop("test_schema")
                quoted_schema = quote_identifier(schema_name)
                quoted_table = f'{quoted_schema}."RUNNER_BACKEND_CHECK"'
                connection = pyexasol.connect(
                    **build_exasol_connect_kwargs(params),
                )
                try:
                    connection.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
                    connection.execute(
                        f"CREATE OR REPLACE TABLE {quoted_table} "
                        "(ID DECIMAL(18, 0), NOTE VARCHAR(200))"
                    )
                    connection.execute(
                        f"INSERT INTO {quoted_table} VALUES "
                        "(1, 'runner-wrapper')"
                    )
                    row = connection.execute(
                        f"SELECT COUNT(*), MIN(NOTE) FROM {quoted_table}"
                    ).fetchone()
                    selected_value = connection.execute("SELECT 42").fetchone()[0]
                    print(
                        json.dumps(
                            to_json_safe(
                                {
                                    "schema": schema_name,
                                    "row_count": row[0],
                                    "note": row[1],
                                    "selected_value": selected_value,
                                }
                            )
                        )
                    )
                finally:
                    try:
                        connection.execute(
                            f"DROP SCHEMA IF EXISTS {quoted_schema} CASCADE"
                        )
                    finally:
                        connection.close()


            if __name__ == "__main__":
                main(sys.argv[1])
            """))
    return script
