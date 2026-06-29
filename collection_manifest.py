"""Helpers for mirroring Galaxy manifest packaging rules in local copy layouts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from noxconfig import PROJECT_CONFIG

PROJECT_ROOT = PROJECT_CONFIG.root_path.resolve()


@dataclass(frozen=True)
class CollectionManifestRules:
    """Supported subset of Galaxy manifest directives used by this project."""

    included_files: frozenset[str]
    included_trees: frozenset[str]

    def includes_path(self, relative_path: str, is_dir: bool) -> bool:
        """Return whether a path belongs in the packaged collection layout."""
        normalized_path = relative_path.strip("/")
        if not normalized_path:
            return True

        if normalized_path in self.included_files:
            return True

        if normalized_path in self.included_trees:
            return True

        if any(normalized_path.startswith(f"{root}/") for root in self.included_trees):
            return True

        if is_dir and any(
            root.startswith(f"{normalized_path}/") for root in self.included_trees
        ):
            return True

        return False


def load_collection_manifest_rules() -> CollectionManifestRules:
    """Load the manifest directives that define the collection archive layout."""
    galaxy = yaml.safe_load((PROJECT_ROOT / "galaxy.yml").read_text(encoding="utf-8"))
    directives = galaxy.get("manifest", {}).get("directives", ())

    included_files: set[str] = set()
    included_trees: set[str] = set()

    for directive in directives:
        parts = directive.split()
        if parts == ["global-exclude", "*"]:
            continue

        if len(parts) == 2 and parts[0] == "include":
            included_files.add(parts[1].strip("/"))
            continue

        if len(parts) == 3 and parts[0] == "recursive-include" and parts[2] == "*":
            included_trees.add(parts[1].strip("/"))
            continue

        raise ValueError(f"Unsupported Galaxy manifest directive: {directive}")

    return CollectionManifestRules(
        included_files=frozenset(included_files),
        included_trees=frozenset(included_trees),
    )


def ignore_collection_manifest_paths(directory: str, names: list[str]) -> set[str]:
    """Return directory entries excluded from the Galaxy collection archive."""
    rules = load_collection_manifest_rules()
    directory_path = Path(directory)
    ignored_names: set[str] = set()

    for name in names:
        path = directory_path / name
        try:
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative_path = name

        if not rules.includes_path(relative_path, is_dir=path.is_dir()):
            ignored_names.add(name)

    return ignored_names
