"""Integration tests for executing Ansible playbooks through ansible-runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from exasol.ansible.playbook import Playbook
from exasol.ansible.runner import (
    AnsibleException,
    Runner,
)


@pytest.mark.integration
def test_ansible_runner_raises_exception_for_failing_playbook(
    ansible_runner_workspace: Any,
) -> None:
    """Verify runner converts ansible-runner failures into AnsibleException."""
    playbook = _write_failing_playbook(ansible_runner_workspace.private_data_dir)

    runner = Runner(
        repositories=(),
        work_dir=ansible_runner_workspace.private_data_dir,
    )

    with pytest.raises(AnsibleException):
        runner.run(
            Playbook(playbook.name),
        )


def _runner_failure_message(result: Any, events: list[dict[str, Any]]) -> str:
    failed_events = [
        event
        for event in events
        if event.get("event") in {"runner_on_failed", "runner_on_unreachable"}
    ]
    event_summaries = []

    for event in failed_events[-3:]:
        event_data = event.get("event_data") or {}
        event_summaries.append(
            {
                "event": event.get("event"),
                "task": event_data.get("task"),
                "host": event_data.get("host"),
                "stdout": event.get("stdout"),
            }
        )

    return (
        f"ansible-runner failed with rc={result.rc}, status={result.status}, "
        f"artifact_dir={result.config.artifact_dir}, failed_events={event_summaries}"
    )


def _write_failing_playbook(private_data_dir: Path) -> Path:
    playbook = private_data_dir / "project" / "runner_failure.yml"
    playbook.write_text("""---
- hosts: localhost
  gather_facts: false
  tasks:
    - name: Force failure
      ansible.builtin.fail:
        msg: boom
""")
    return playbook
