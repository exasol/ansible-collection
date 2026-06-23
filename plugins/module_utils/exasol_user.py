"""Ansible module utility shim for the exasol_user runtime implementation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from exasol.ansible_modules.common_runtime_import import (
    load_runtime_module,
)

RUNTIME_MODULE = "exasol.ansible_modules.exasol_user"
RUNTIME_MODULE_NAME = "_exasol_ansible_modules_exasol_user"


def ensure_user(*args: Any, **kwargs: Any) -> dict[str, object]:
    """Delegate to the exasol_user runtime implementation."""
    return _runtime().ensure_user(*args, **kwargs)


def normalized_exasol_error_message(*args: Any, **kwargs: Any) -> str:
    """Delegate to the exasol_user runtime implementation."""
    return _runtime().normalized_exasol_error_message(*args, **kwargs)


def sanitize_error_message(*args: Any, **kwargs: Any) -> str:
    """Delegate to the exasol_user runtime implementation."""
    return _runtime().sanitize_error_message(*args, **kwargs)


def _runtime() -> ModuleType:
    return load_runtime_module(
        module_name=RUNTIME_MODULE,
        source_module_name=RUNTIME_MODULE_NAME,
        source_path=_runtime_source_path(),
        description="user runtime implementation",
    )


def _runtime_source_path() -> Path:
    collection_root = Path(__file__).resolve().parents[2]

    return collection_root / "exasol" / "ansible_modules" / "exasol_user.py"


__all__ = [
    "ensure_user",
    "normalized_exasol_error_message",
    "sanitize_error_message",
]
