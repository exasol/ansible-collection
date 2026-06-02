"""Tests for the Ansible runner wrapper module utility."""

from __future__ import annotations

from unittest.mock import Mock

from plugins.module_utils.ansible_runner_wrapper import (
    REQUIRED_PACKAGE,
    require_ansible_runner_wrapper,
)


def test_require_ansible_runner_wrapper_returns_wrapper() -> None:
    """Verify collection code delegates to the released wrapper package."""
    wrapper = require_ansible_runner_wrapper(Mock())

    assert hasattr(wrapper, "Runner")
    assert hasattr(wrapper, "Playbook")
    assert hasattr(wrapper, "ImportlibRepository")


def test_required_package_name_is_declared() -> None:
    """Verify error messages point users to the package dependency."""
    assert REQUIRED_PACKAGE == "exasol-ansible-runner-wrapper"
