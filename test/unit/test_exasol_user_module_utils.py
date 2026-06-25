"""Tests for collection-native exasol_user runtime surface."""

from __future__ import annotations

from exasol.ansible_modules import exasol_user


def test_user_runtime_public_surface_is_focused_on_user_management() -> None:
    """Verify user runtime does not duplicate shared connection helpers."""
    assert hasattr(exasol_user, "ensure_user")
    assert hasattr(exasol_user, "normalized_exasol_error_message")
    assert hasattr(exasol_user, "sanitize_error_message")

    assert not hasattr(exasol_user, "build_exasol_connect_kwargs")
    assert not hasattr(exasol_user, "exasol_connection_argument_spec")
