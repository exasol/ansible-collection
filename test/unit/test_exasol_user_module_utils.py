"""Tests for collection-native exasol_user module utility helpers."""

from __future__ import annotations

from pathlib import Path

from plugins.module_utils import exasol_user


def test_runtime_source_path_uses_collection_root() -> None:
    """Verify source-layout fallback is derived from the module file path."""
    assert exasol_user._runtime_source_path() == (
        Path(exasol_user.__file__).resolve().parents[2]
        / "exasol"
        / "ansible_modules"
        / "exasol_user.py"
    )


def test_module_utils_public_surface_is_focused_on_user_management() -> None:
    """Verify the shim does not duplicate shared connection helpers."""
    assert exasol_user.__all__ == [
        "ensure_user",
        "normalized_exasol_error_message",
        "sanitize_error_message",
    ]

    assert not hasattr(exasol_user, "build_exasol_connect_kwargs")
    assert not hasattr(exasol_user, "exasol_connection_argument_spec")
