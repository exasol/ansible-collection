"""Tests for direct runtime imports in collection module entry points."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

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


def test_exasol_user_plugin_uses_direct_user_and_query_runtimes() -> None:
    """Verify exasol_user no longer imports through plugins/module_utils."""
    module = _load_plugin_module("exasol_user")

    assert module.exasol_query_utils is exasol_query
    assert module.exasol_user_utils is exasol_user


def test_plugin_modules_do_not_reference_collection_module_utils() -> None:
    """Verify module entry points do not depend on the removed shim package."""
    for module_name in ("exasol_query", "exasol_user"):
        source = (PLUGIN_MODULES / f"{module_name}.py").read_text(encoding="utf-8")

        assert "plugins.module_utils" not in source
        assert "ansible_collections.exasol.exasol.plugins.module_utils" not in source


@pytest.mark.parametrize("module_name", ["exasol_query", "exasol_user"])
def test_plugin_modules_bootstrap_collection_root_for_direct_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    """Verify direct runtime imports work in Ansible's isolated sanity imports."""
    project_root = str(PROJECT_ROOT)
    monkeypatch.setattr(
        sys,
        "path",
        [path for path in sys.path if Path(path or ".").resolve() != PROJECT_ROOT],
    )
    _remove_cached_exasol_modules(monkeypatch)

    _load_plugin_module(module_name)

    assert sys.path[0] == project_root


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


def _remove_cached_exasol_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    for module_name in list(sys.modules):
        if module_name == "exasol" or module_name.startswith("exasol."):
            monkeypatch.delitem(sys.modules, module_name)
