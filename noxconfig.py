"""Project configuration for toolbox-provided Nox sessions."""

from __future__ import annotations

from pathlib import Path

import nox

from exasol.toolbox.config import (
    BaseConfig,
    ValidVersionStr,
)
from exasol.toolbox.nox.plugin import hookimpl
from exasol.toolbox.util.version import Version

from release_version import sync_release_versions_to


class ProjectConfig(BaseConfig):
    """Project-specific Nox configuration."""

    ansible_test_python_versions: tuple[ValidVersionStr, ...]


class ReleaseVersionSyncPlugin:
    """Sync collection release artifacts when the toolbox prepares a release."""

    _FILES = (
        Path("galaxy.yml"),
        Path("requirements.txt"),
        Path("meta") / "ee-requirements.txt",
    )

    @hookimpl
    def prepare_release_update_version(self, session: nox.Session, config: ProjectConfig, version: Version) -> None:
        """Update derived release files after pyproject.toml was bumped."""
        synchronized_version = sync_release_versions_to(
            config.root_path, str(version)
        )
        if synchronized_version != str(version):
            session.error(
                "release:prepare synchronized release artifacts to "
                f"{synchronized_version} instead of {version}."
            )

    @hookimpl
    def prepare_release_add_files(self, session: nox.Session, config: ProjectConfig) -> list[Path]:
        """Add synchronized release artifacts to the prepare-release commit."""
        return [config.root_path / path for path in self._FILES]


PROJECT_CONFIG = ProjectConfig(
    project_name="ansible_modules",
    root_path=Path(__file__).parent,
    python_versions=("3.11", "3.12", "3.13"),
    exasol_versions=("8.29.13", "2025.1.8"),
    plugins_for_nox_sessions=(ReleaseVersionSyncPlugin,),
    # The current Ansible 10 / ansible-core 2.17 test dependency does not
    # support Python 3.13. Keep ansible-test limited to supported interpreters
    # until the collection test dependency is upgraded.
    ansible_test_python_versions=("3.11", "3.12"),
)
