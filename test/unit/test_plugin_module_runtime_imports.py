"""Tests for direct runtime imports in collection module entry points."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from exasol.ansible_modules import (
    exasol_query,
    exasol_user,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_MODULES = PROJECT_ROOT / "plugins" / "modules"
REMOVED_QUERY_MODULE_UTILS_SURFACE = [
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
REMOVED_USER_MODULE_UTILS_SURFACE = [
    "ensure_user",
    "normalized_exasol_error_message",
    "sanitize_error_message",
]


def test_exasol_query_plugin_uses_direct_query_runtime() -> None:
    """Verify exasol_query no longer imports through plugins/module_utils."""
    module = _load_plugin_module("exasol_query")

    assert module.exasol_query_utils is exasol_query


def test_direct_query_runtime_keeps_removed_module_utils_surface() -> None:
    """Verify all former exasol_query shim functions remain directly available."""
    for function_name in REMOVED_QUERY_MODULE_UTILS_SURFACE:
        assert hasattr(exasol_query, function_name)


def test_direct_user_runtime_keeps_removed_module_utils_surface() -> None:
    """Verify all former exasol_user shim functions remain directly available."""
    for function_name in REMOVED_USER_MODULE_UTILS_SURFACE:
        assert hasattr(exasol_user, function_name)


def _load_plugin_module(module_name: str) -> ModuleType:
    module_path = PLUGIN_MODULES / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(
        f"_test_plugins_modules_{module_name}",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
