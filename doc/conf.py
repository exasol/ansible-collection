"""Sphinx configuration for the Exasol Ansible collection."""

from __future__ import annotations

# Sphinx expects these configuration variables to use lower-case names.
# pylint: disable=invalid-name

project = "ansible-collection"
copyright = "2026, Exasol"  # pylint: disable=redefined-builtin
author = "Exasol"

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
    "exasol.toolbox.sphinx.multiversion",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "shibuya"
html_title = "ansible-collection"

linkcheck_rate_limit_timeout = 60
linkcheck_timeout = 15
linkcheck_delay = 30
linkcheck_retries = 2
linkcheck_anchors = False
linkcheck_ignore: list[str] = []
