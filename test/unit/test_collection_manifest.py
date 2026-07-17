"""Tests for local copy layouts derived from the Galaxy collection manifest."""

from __future__ import annotations

import subprocess
from pathlib import Path

from collection_manifest import ignore_collection_manifest_paths
from noxconfig import PROJECT_CONFIG
from noxfile import (
    _ansible_env,
    _ignore_ansible_test_source_paths,
    _initialize_temporary_git_repository,
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
        [".git", ".nox", "exasol", "galaxy.yml", "plugins", "test", "tests"],
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


def test_ansible_env_keeps_temporary_files_inside_session_root(tmp_path: Path) -> None:
    """Verify nested Ansible commands do not fall back to global /tmp."""
    env = _ansible_env(tmp_path)

    assert env["TMPDIR"] == str(tmp_path / ".tmp")
    assert (tmp_path / ".tmp").is_dir()


def test_temporary_git_repository_supports_ansible_test_file_discovery(
    tmp_path: Path,
) -> None:
    """Verify ansible-test can discover copied source files through Git."""
    module_path = tmp_path / "plugins" / "modules" / "example.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("# example\n", encoding="utf-8")

    _initialize_temporary_git_repository(tmp_path)

    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    discovered_paths = result.stdout.decode("utf-8").split("\0")
    assert "plugins/modules/example.py" in discovered_paths
