"""Tests for local copy layouts derived from the Galaxy collection manifest."""

from __future__ import annotations

from pathlib import Path

from collection_manifest import ignore_collection_manifest_paths
from noxconfig import PROJECT_CONFIG
from noxfile import (
    _ignore_ansible_test_source_paths,
)

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


def test_manifest_ignore_excludes_repository_only_paths() -> None:
    """Verify local build copies follow the Galaxy archive manifest."""
    ignored = ignore_collection_manifest_paths(
        str(PROJECT_ROOT),
        [
            ".build_output",
            ".git",
            ".nox",
            "LICENSE",
            "README.md",
            "exasol",
            "meta",
            "plugins",
            "requirements.txt",
            "roles",
            "test",
        ],
    )

    assert ignored == {".build_output", ".git", ".nox", "exasol", "test"}


def test_manifest_ignore_keeps_recursive_include_descendants(tmp_path: Path) -> None:
    """Verify recursive manifest includes keep subtree directories in copytree."""
    plugins_dir = PROJECT_ROOT / "plugins"
    kept = ignore_collection_manifest_paths(
        str(plugins_dir),
        ["doc_fragments", "modules"],
    )

    assert kept == set()


def test_ansible_test_layout_keeps_source_runtime_package() -> None:
    """Verify ansible-test copies retain source-only runtime and target paths."""
    ignored = _ignore_ansible_test_source_paths(
        str(PROJECT_ROOT),
        [".git", ".nox", "exasol", "plugins", "test", "tests"],
    )

    assert ignored == {".git", ".nox", "test"}


def test_ansible_test_layout_keeps_integration_target_subtree() -> None:
    """Verify ansible-test copies retain integration target directories."""
    tests_root = PROJECT_ROOT / "tests"
    ignored = _ignore_ansible_test_source_paths(
        str(tests_root),
        ["integration"],
    )

    assert ignored == set()
