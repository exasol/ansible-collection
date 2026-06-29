"""Ansible sanity compatibility for source-tree runtime imports.

This module_utils file is intentionally limited to the ansible-test import
workaround. Runtime implementation stays in the PyPI package under
exasol.ansible_modules.
"""

from __future__ import annotations

import sys
from pathlib import Path


def make_source_runtime_importable_for_ansible_sanity(module_file: str) -> None:
    """Expose the source-tree runtime package to ansible-test sanity imports."""
    # Test-only compatibility hook: ansible-test imports modules in isolated
    # sanity venvs before the PyPI runtime package is installed. Adding the
    # source checkout root here is the smallest fix; duplicating argument specs
    # or restoring runtime helpers under plugins/module_utils would be worse.
    module_path = Path(module_file).resolve()
    modules_dir = module_path.parent
    plugins_dir = modules_dir.parent
    if modules_dir.name != "modules" or plugins_dir.name != "plugins":
        return

    collection_root = str(plugins_dir.parent)
    if collection_root not in sys.path:
        sys.path.insert(0, collection_root)
