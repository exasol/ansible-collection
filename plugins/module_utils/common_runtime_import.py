"""Runtime loading helpers for Ansible module utility shims."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any


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

    source_path = Path(source_path).resolve()
    _ensure_collection_root_on_path(source_path)

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


def _ensure_collection_root_on_path(source_path: Path) -> None:
    collection_root = source_path.parents[2]
    collection_root_text = str(collection_root)
    if collection_root_text not in sys.path:
        sys.path.insert(0, collection_root_text)
