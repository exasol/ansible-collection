"""Shared runtime helpers for Exasol Ansible modules."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections.abc import (
    Collection,
    Mapping,
)
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

QUERY_RUNTIME_MODULE = "exasol.ansible_modules.exasol_query"
QUERY_RUNTIME_MODULE_NAME = "_exasol_ansible_modules_exasol_query"


def choice_string(
    params: Mapping[str, object],
    name: str,
    default: str,
    choices: Collection[str],
) -> str:
    """Return a string option value after validating it against allowed choices."""
    value = params.get(name, default)

    if not isinstance(value, str) or value not in choices:
        choice_list = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {choice_list}.")

    return value


def required_string(params: Mapping[str, object], name: str) -> str:
    """Return a required non-empty string option value."""
    value = params.get(name)

    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string.")

    return value


def sibling_query_runtime(source_file: str) -> ModuleType:
    """Load the shared query runtime from package import or a sibling source file."""
    return load_runtime_module(
        module_name=QUERY_RUNTIME_MODULE,
        source_module_name=QUERY_RUNTIME_MODULE_NAME,
        source_path=Path(source_file).resolve().with_name("exasol_query.py"),
        description="query runtime implementation",
    )


def load_runtime_module(
    module_name: str,
    source_module_name: str,
    source_path: Path,
    description: str,
) -> ModuleType:
    """Load a runtime module by package name, then by explicit source file."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return runtime_from_source_file(source_module_name, source_path, description)


def runtime_from_source_file(
    source_module_name: str,
    source_path: Path,
    description: str,
) -> ModuleType:
    """Load a runtime implementation from a source file path."""
    cached_runtime = sys.modules.get(source_module_name)
    if cached_runtime is not None:
        return cached_runtime

    spec, loader = source_runtime_spec_and_loader(
        source_module_name,
        source_path,
        description,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[source_module_name] = module
    loader.exec_module(module)
    return module


def source_runtime_spec_and_loader(
    source_module_name: str,
    source_path: Path,
    description: str,
) -> tuple[ModuleSpec, Any]:
    """Return the import spec and loader for a runtime source file."""
    spec = importlib.util.spec_from_file_location(source_module_name, source_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {description} from {source_path}")

    return spec, spec.loader
