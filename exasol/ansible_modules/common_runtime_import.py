"""Shared runtime loading helpers for Exasol Ansible modules."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

QUERY_RUNTIME_MODULE = "exasol.ansible_modules.exasol_query"
QUERY_RUNTIME_MODULE_NAME = "_exasol_ansible_modules_exasol_query"


def query_runtime() -> ModuleType:
    return _sibling_query_runtime(__file__)


def load_runtime_module(
        module_name: str,
        source_module_name: str,
        source_path: Path,
        description: str,
) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return runtime_from_source_file(source_module_name, source_path, description)


def runtime_from_source_file(
        source_module_name: str,
        source_path: Path,
        description: str,
) -> ModuleType:
    cached_runtime = sys.modules.get(source_module_name)
    if cached_runtime is not None:
        return cached_runtime

    # ensure deterministic absolute path (fixes CI file resolution issues)
    source_path = Path(source_path)

    spec, loader = source_runtime_spec_and_loader(
        source_module_name,
        source_path,
        description,
    )

    module = importlib.util.module_from_spec(spec)
    sys.modules[source_module_name] = module

    loader.exec_module(module)  # type: ignore[union-attr]
    return module


def source_runtime_spec_and_loader(
        source_module_name: str,
        source_path: Path,
        description: str,
) -> tuple[ModuleSpec, Any]:
    spec = importlib.util.spec_from_file_location(source_module_name, str(source_path))

    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {description} from {source_path}")

    return spec, spec.loader


def _sibling_query_runtime(source_file: str) -> ModuleType:
    return load_runtime_module(
        module_name=QUERY_RUNTIME_MODULE,
        source_module_name=QUERY_RUNTIME_MODULE_NAME,
        source_path=Path(source_file).resolve().with_name("exasol_query.py"),
        description="query runtime implementation",
    )