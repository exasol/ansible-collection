"""Tests for collection runtime helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from exasol.ansible_collection.runtime import (
    CollectionRuntimeError,
    fail_json_on_missing_dependency,
    missing_dependency_message,
)


def test_missing_dependency_message() -> None:
    """Verify missing dependency messages name the execution environment."""
    assert missing_dependency_message("example-package") == (
        "Python package 'example-package' is required. Install it in the "
        "Ansible execution environment."
    )


def test_fail_json_on_missing_dependency() -> None:
    """Verify helpers fail Ansible modules with a clear dependency message."""
    module = Mock()
    error = ImportError("example")

    with pytest.raises(CollectionRuntimeError):
        fail_json_on_missing_dependency(module, "example-package", error)

    module.fail_json.assert_called_once_with(
        msg=missing_dependency_message("example-package"),
        exception="example",
    )
