"""Tests for shared runtime helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from exasol.ansible_modules import common_runtime_import
from exasol.ansible_modules.common_identifier_validation import (
    quote_identifier,
    validate_identifier,
    validate_object_name,
    validate_role_name,
    validate_schema_name,
    validate_user_name,
)
from exasol.ansible_modules.common_param_validation import (
    validate_choice_param,
    validate_required_param,
)

from exasol.ansible_modules.common_runtime_import import (
    QUERY_RUNTIME_MODULE_NAME,
    load_runtime_module,
    runtime_from_source_file,
    source_runtime_spec_and_loader,
)

RUNTIME_DIR = Path(__file__).resolve().parents[2] / "exasol" / "ansible_modules"


def test_choice_string_accepts_valid_values() -> None:
    """Verify choice string options are returned after validation."""
    assert (
        validate_choice_param(
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
        validate_choice_param({}, "state", "present", {"present", "absent"})
        == "present"
    )


def test_choice_string_rejects_invalid_values() -> None:
    """Verify invalid choice values fail with an actionable message."""
    with pytest.raises(ValueError, match="state must be one of"):
        validate_choice_param(
            {"state": "invalid"},
            "state",
            "present",
            {"present", "absent"},
        )


def test_required_string_accepts_non_empty_string() -> None:
    """Verify required string options are returned after validation."""
    assert validate_required_param({"name": "app_user"}, "name") == "app_user"


@pytest.mark.parametrize("value", [None, "", object()])
def test_required_string_rejects_invalid_values(value: object) -> None:
    """Verify required string options must be non-empty strings."""
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        validate_required_param({"name": value}, "name")


def test_load_runtime_module_falls_back_to_source_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify runtime loading falls back to source-file loading."""
    runtime = ModuleType("runtime")

    def import_module(name: str) -> ModuleType:
        assert name == "missing.module"
        raise ImportError("missing package import")

    def fake_runtime_from_source_file(
        source_module_name: str,
        source_path: Path,
        description: str,
    ) -> ModuleType:
        assert source_module_name == "source.module"
        assert source_path == Path("runtime.py")
        assert description == "runtime implementation"
        return runtime

    monkeypatch.setattr(
        "exasol.ansible_modules.common_runtime_import.importlib.import_module",
        import_module,
    )
    monkeypatch.setattr(
        common_runtime_import,
        "runtime_from_source_file",
        fake_runtime_from_source_file,
    )

    assert (
        load_runtime_module(
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
            runtime_from_source_file(
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
    previous = sys.modules.pop(QUERY_RUNTIME_MODULE_NAME, None)

    try:
        runtime = runtime_from_source_file(
            QUERY_RUNTIME_MODULE_NAME,
            RUNTIME_DIR / "exasol_query.py",
            "query runtime implementation",
        )

        assert runtime.__name__ == QUERY_RUNTIME_MODULE_NAME
        assert hasattr(runtime, "execute_queries")
    finally:
        sys.modules.pop(QUERY_RUNTIME_MODULE_NAME, None)
        if previous is not None:
            sys.modules[QUERY_RUNTIME_MODULE_NAME] = previous


def test_source_runtime_spec_loader_failure_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify source runtime loading fails clearly when no loader is available."""

    monkeypatch.setattr(
        common_runtime_import.importlib.util,
        "spec_from_file_location",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(ImportError, match="Cannot load query runtime"):
        source_runtime_spec_and_loader(
            QUERY_RUNTIME_MODULE_NAME,
            Path("exasol_query.py"),
            "query runtime implementation",
        )


def test_identifier_validation_helpers_accept_regular_identifiers() -> None:
    """Verify schema, user, role, and object identifier helpers."""
    assert validate_schema_name("APP_SCHEMA") == "APP_SCHEMA"
    assert validate_user_name("APP_USER1") == "APP_USER1"
    assert validate_role_name("APP_ROLE") == "APP_ROLE"
    assert validate_object_name("APP_SCHEMA.TABLE1") == "APP_SCHEMA.TABLE1"
    assert (
        quote_identifier(
            "app_schema.table1",
            allow_qualified=True,
        )
        == '"APP_SCHEMA"."TABLE1"'
    )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "1APP",
        "APP-TABLE",
        "APP TABLE",
        "APPÄ",
        "APP.TABLE.EXTRA",
        f"A{'B' * 128}",
    ],
)
def test_identifier_validation_helpers_reject_invalid_schema_names(name: str) -> None:
    """Verify invalid identifiers are rejected before dynamic SQL generation."""
    with pytest.raises(ValueError):
        validate_schema_name(name)


def test_object_identifier_validation_rejects_too_many_parts() -> None:
    """Verify object names are limited to schema.object qualification."""
    with pytest.raises(ValueError):
        validate_object_name("APP.TABLE.EXTRA")


@pytest.mark.parametrize("identifier", [object(), ""])
def test_validate_identifier_rejects_invalid_name_types(identifier: object) -> None:
    """Verify identifier validation rejects non-string and empty values directly."""
    with pytest.raises(ValueError):
        validate_identifier(identifier)  # type: ignore[arg-type]
