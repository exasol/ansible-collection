"""Tests for the Ansible runner wrapper test dependency."""

from __future__ import annotations

import importlib


def test_ansible_runner_wrapper_is_available_for_tests() -> None:
    """Verify tests can use the wrapper without making it a runtime dependency."""
    wrapper = importlib.import_module("exasol.ansible")

    assert hasattr(wrapper, "Playbook")
    assert hasattr(wrapper, "ImportlibRepository")
    assert hasattr(wrapper, "Runner")
