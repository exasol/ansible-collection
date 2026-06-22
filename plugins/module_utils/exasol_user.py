"""Ansible module utility shim for the exasol_user runtime implementation."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

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
    errors = []
    try:
        return importlib.import_module(RUNTIME_MODULE)
    except ImportError as error:
        errors.append(f"{RUNTIME_MODULE}: {error}")

    try:
        return _runtime_from_source_file()
    except ImportError as error:
        errors.append(str(error))

    raise ImportError(
        "Unable to import exasol_user runtime implementation. " + "; ".join(errors)
    )


def _runtime_from_source_file() -> ModuleType:
    cached_runtime = sys.modules.get(RUNTIME_MODULE_NAME)
    if cached_runtime is not None:
        return cached_runtime

    spec, loader = _source_runtime_spec_and_loader(_runtime_source_path())
    module = importlib.util.module_from_spec(spec)
    sys.modules[RUNTIME_MODULE_NAME] = module
    loader.exec_module(module)
    return module


def _source_runtime_spec_and_loader(runtime_path: Path) -> tuple[ModuleSpec, Any]:
    spec = importlib.util.spec_from_file_location(RUNTIME_MODULE_NAME, runtime_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load runtime implementation from {runtime_path}")

    return spec, spec.loader


def _runtime_source_path() -> Path:
    collection_root = Path(__file__).resolve().parents[2]

    return collection_root / "exasol" / "ansible_modules" / "exasol_user.py"


__all__ = [
    "ensure_user",
    "normalized_exasol_error_message",
    "sanitize_error_message",
]
