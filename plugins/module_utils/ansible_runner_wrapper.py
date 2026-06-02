"""Adapter for delegating collection modules to exasol-ansible-runner-wrapper."""

from __future__ import annotations

import importlib
from typing import Any

_ansible: Any | None = None
_IMPORT_ERROR: ImportError | None = None

try:
    _ansible = importlib.import_module("exasol.ansible")
except ImportError as ex:
    _IMPORT_ERROR = ex

REQUIRED_PACKAGE = "exasol-ansible-runner-wrapper"


def require_ansible_runner_wrapper(module: Any) -> Any:
    """Return the wrapper module or fail the Ansible module with a clear message."""
    if _ansible is not None:
        return _ansible

    module.fail_json(
        msg=(
            f"Python package '{REQUIRED_PACKAGE}' is required. Install it in the "
            "Ansible execution environment."
        ),
        exception=str(_IMPORT_ERROR),
    )
