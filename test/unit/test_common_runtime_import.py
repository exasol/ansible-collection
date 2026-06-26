"""Tests for source-tree runtime import support."""

from __future__ import annotations

import sys
from pathlib import Path

from plugins.module_utils.common_runtime_import import (
    make_source_runtime_importable_for_ansible_sanity,
)


def test_make_source_runtime_importable_adds_collection_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify module paths under plugins/modules expose the collection root."""
    module_file = tmp_path / "plugins" / "modules" / "exasol_query.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    monkeypatch.setattr(sys, "path", ["existing"])

    make_source_runtime_importable_for_ansible_sanity(str(module_file))

    assert sys.path == [str(tmp_path), "existing"]


def test_make_source_runtime_importable_does_not_duplicate_collection_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify an existing collection root keeps its position on sys.path."""
    module_file = tmp_path / "plugins" / "modules" / "exasol_user.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    monkeypatch.setattr(sys, "path", [str(tmp_path), "existing"])

    make_source_runtime_importable_for_ansible_sanity(str(module_file))

    assert sys.path == [str(tmp_path), "existing"]


def test_make_source_runtime_importable_ignores_unexpected_layout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Verify unrelated file layouts do not change sys.path."""
    module_file = tmp_path / "not_plugins" / "modules" / "exasol_query.py"
    module_file.parent.mkdir(parents=True)
    module_file.touch()
    monkeypatch.setattr(sys, "path", ["existing"])

    make_source_runtime_importable_for_ansible_sanity(str(module_file))

    assert sys.path == ["existing"]
