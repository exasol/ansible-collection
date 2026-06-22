"""Tests for shared runtime helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from exasol.ansible_modules import common


def test_choice_string_accepts_valid_values() -> None:
    """Verify choice string options are returned after validation."""
    assert (
        common.validate_choice_param(
            {"state": "absent"},
            "state",
            "present",
            {"present", "absent"},
        )
        == "absent"
    )


def test_choice_string_uses_default_value() -> None:
    """Verify missing choice string options use the provided default."""
    assert (
        common.validate_choice_param({}, "state", "present", {"present", "absent"})
        == "present"
    )


def test_choice_string_rejects_invalid_values() -> None:
    """Verify invalid choice values fail with an actionable message."""
    with pytest.raises(ValueError, match="state must be one of"):
        common.validate_choice_param(
            {"state": "invalid"},
            "state",
            "present",
            {"present", "absent"},
        )


def test_required_string_accepts_non_empty_string() -> None:
    """Verify required string options are returned after validation."""
    assert common.validate_required_param({"name": "app_user"}, "name") == "app_user"


@pytest.mark.parametrize("value", [None, "", object()])
def test_required_string_rejects_invalid_values(value: object) -> None:
    """Verify required string options must be non-empty strings."""
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        common.validate_required_param({"name": value}, "name")


def test_load_runtime_module_falls_back_to_source_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify runtime loading falls back to source-file loading."""
    runtime = ModuleType("runtime")

    def import_module(name: str) -> ModuleType:
        assert name == "missing.module"
        raise ImportError("missing package import")

    def runtime_from_source_file(
        source_module_name: str,
        source_path: Path,
        description: str,
    ) -> ModuleType:
        assert source_module_name == "source.module"
        assert source_path == Path("runtime.py")
        assert description == "runtime implementation"
        return runtime

    monkeypatch.setattr(common.importlib, "import_module", import_module)
    monkeypatch.setattr(
        common,
        "runtime_from_source_file",
        runtime_from_source_file,
    )

    assert (
        common.load_runtime_module(
            module_name="missing.module",
            source_module_name="source.module",
            source_path=Path("runtime.py"),
            description="runtime implementation",
        )
        is runtime
    )


def test_runtime_from_source_file_returns_cached_module() -> None:
    """Verify source runtime loading reuses an already cached module."""
    runtime = ModuleType("cached_runtime")
    source_module_name = "_test_cached_runtime"
    previous = sys.modules.get(source_module_name)
    sys.modules[source_module_name] = runtime
    try:
        assert (
            common.runtime_from_source_file(
                source_module_name,
                Path("runtime.py"),
                "runtime implementation",
            )
            is runtime
        )
    finally:
        if previous is None:
            sys.modules.pop(source_module_name, None)
        else:
            sys.modules[source_module_name] = previous


def test_runtime_from_source_file_loads_query_runtime() -> None:
    """Verify source runtime loading can import the sibling query module."""
    previous = sys.modules.pop(common.QUERY_RUNTIME_MODULE_NAME, None)
    try:
        runtime = common.runtime_from_source_file(
            common.QUERY_RUNTIME_MODULE_NAME,
            Path(common.__file__).resolve().with_name("exasol_query.py"),
            "query runtime implementation",
        )
        assert runtime.__name__ == common.QUERY_RUNTIME_MODULE_NAME
        assert hasattr(runtime, "execute_queries")
    finally:
        sys.modules.pop(common.QUERY_RUNTIME_MODULE_NAME, None)
        if previous is not None:
            sys.modules[common.QUERY_RUNTIME_MODULE_NAME] = previous


def test_source_runtime_spec_loader_failure_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify source runtime loading fails clearly when no loader is available."""
    monkeypatch.setattr(
        common.importlib.util,
        "spec_from_file_location",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(ImportError, match="Cannot load query runtime"):
        common.source_runtime_spec_and_loader(
            common.QUERY_RUNTIME_MODULE_NAME,
            Path(common.__file__).resolve().with_name("exasol_query.py"),
            "query runtime implementation",
        )
