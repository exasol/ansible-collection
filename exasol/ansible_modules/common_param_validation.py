"""Shared validation helpers for Exasol Ansible modules."""

from collections.abc import (
    Collection,
    Mapping,
)


def validate_choice_param(
    params: Mapping[str, object],
    name: str,
    default: str,
    choices: Collection[str],
) -> str:
    """Validate and return a string choice parameter."""
    value = params.get(name, default)

    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string. Got: {type(value).__name__}.")

    if value not in choices:
        choice_list = ", ".join(sorted(choices))
        raise ValueError(f"{name} must be one of: {choice_list}. Got: {value!r}.")

    return value


def validate_required_param(params: Mapping[str, object], name: str) -> str:
    """Validate and return a required non-empty string parameter."""
    value = params.get(name)

    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string.")

    return value
