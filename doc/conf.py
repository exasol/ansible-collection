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

# Route ```mermaid fenced code blocks to sphinxcontrib-mermaid's `mermaid`
# directive instead of treating them as a literal code block that needs a
# (nonexistent) "mermaid" Pygments lexer.
myst_fence_as_directive = ["mermaid"]

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
