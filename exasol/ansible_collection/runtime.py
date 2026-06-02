"""Shared runtime helpers for collection plugins and modules."""

from __future__ import annotations

from typing import (
    Any,
    NoReturn,
)


class CollectionRuntimeError(RuntimeError):
    """Raised when collection runtime support cannot continue."""


def missing_dependency_message(package: str) -> str:
    """Return a user-facing message for missing execution-environment packages."""
    return (
        f"Python package '{package}' is required. Install it in the Ansible "
        "execution environment."
    )


def fail_json_on_missing_dependency(
    module: Any,
    package: str,
    error: BaseException,
) -> NoReturn:
    """Fail an Ansible module because a runtime Python dependency is missing."""
    module.fail_json(
        msg=missing_dependency_message(package),
        exception=str(error),
    )
    raise CollectionRuntimeError(missing_dependency_message(package))
