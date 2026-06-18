"""Ansible module utility shim for the exasol_query runtime implementation."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any

RUNTIME_MODULE = "exasol.ansible_modules.exasol_query"
RUNTIME_MODULE_NAME = "_exasol_ansible_modules_exasol_query"


def build_exasol_connect_kwargs(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().build_exasol_connect_kwargs(*args, **kwargs)


def build_exasol_dsn(*args: Any, **kwargs: Any) -> str:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().build_exasol_dsn(*args, **kwargs)


def connection_parameters_with_defaults(
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().connection_parameters_with_defaults(*args, **kwargs)


def exasol_connection_argument_spec() -> dict[str, dict[str, Any]]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().exasol_connection_argument_spec()


def execute_queries(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().execute_queries(*args, **kwargs)


def fetch_result_rows(*args: Any, **kwargs: Any) -> list[Any]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().fetch_result_rows(*args, **kwargs)


def is_authentication_error(*args: Any, **kwargs: Any) -> bool:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().is_authentication_error(*args, **kwargs)


def is_read_only_query(*args: Any, **kwargs: Any) -> bool:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().is_read_only_query(*args, **kwargs)


def normalize_query_list(*args: Any, **kwargs: Any) -> list[str]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().normalize_query_list(*args, **kwargs)


def normalized_exasol_error_message(*args: Any, **kwargs: Any) -> str:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().normalized_exasol_error_message(*args, **kwargs)


def prepare_query(*args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().prepare_query(*args, **kwargs)


def rows_to_json_safe(*args: Any, **kwargs: Any) -> list[Any]:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().rows_to_json_safe(*args, **kwargs)


def sanitize_error_message(*args: Any, **kwargs: Any) -> str:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().sanitize_error_message(*args, **kwargs)


def statement_execution_time_ms(*args: Any, **kwargs: Any) -> float:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().statement_execution_time_ms(*args, **kwargs)


def statement_rowcount(*args: Any, **kwargs: Any) -> int:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().statement_rowcount(*args, **kwargs)


def to_json_safe(*args: Any, **kwargs: Any) -> Any:
    """Delegate to the exasol_query runtime implementation."""
    return _runtime().to_json_safe(*args, **kwargs)


def _runtime() -> ModuleType:
    errors = []
    # Happy path. For example: this repo was installed into the active Python env
    # with `pip install -e .`, so `exasol.ansible_modules.exasol_query` imports.
    try:
        return importlib.import_module(RUNTIME_MODULE)
    except ImportError as error:
        errors.append(f"{RUNTIME_MODULE}: {error}")

    # Fallback scenario: Ansible is executing the collection from a checkout or
    # collection install, so load the same runtime from the source tree instead.
    try:
        return _runtime_from_source_file()
    except ImportError as error:
        errors.append(str(error))

    raise ImportError(
        "Unable to import exasol_query runtime implementation. " + "; ".join(errors)
    )


def _runtime_from_source_file() -> ModuleType:
    cached_runtime = _cached_source_runtime()
    if cached_runtime is not None:
        return cached_runtime

    spec, loader = _source_runtime_spec_and_loader(_runtime_source_path())
    return _load_source_runtime(spec, loader)


def _cached_source_runtime() -> ModuleType | None:
    return sys.modules.get(RUNTIME_MODULE_NAME)


def _source_runtime_spec_and_loader(runtime_path: Path) -> tuple[ModuleSpec, Any]:
    spec = importlib.util.spec_from_file_location(RUNTIME_MODULE_NAME, runtime_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load runtime implementation from {runtime_path}")

    return spec, spec.loader


def _load_source_runtime(spec: ModuleSpec, loader: Any) -> ModuleType:
    module = importlib.util.module_from_spec(spec)
    sys.modules[RUNTIME_MODULE_NAME] = module
    loader.exec_module(module)
    return module


def _runtime_source_path() -> Path:
    collection_root = Path(__file__).resolve().parents[2]

    return collection_root / "exasol" / "ansible_modules" / "exasol_query.py"


__all__ = [
    "build_exasol_connect_kwargs",
    "build_exasol_dsn",
    "connection_parameters_with_defaults",
    "execute_queries",
    "exasol_connection_argument_spec",
    "fetch_result_rows",
    "is_authentication_error",
    "is_read_only_query",
    "normalize_query_list",
    "normalized_exasol_error_message",
    "prepare_query",
    "rows_to_json_safe",
    "sanitize_error_message",
    "statement_execution_time_ms",
    "statement_rowcount",
    "to_json_safe",
]
