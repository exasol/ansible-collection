"""Static checks for the pytest integration backend setup."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_CONFTEST = PROJECT_ROOT / "test" / "integration" / "conftest.py"


def test_pytest_configure_pins_backend_option_to_onprem() -> None:
    """Verify the compatibility alias cannot enable a backend matrix."""
    conftest = _load_integration_conftest()
    config = SimpleNamespace(option=SimpleNamespace(backend=["all"]))

    conftest.pytest_configure(config)

    assert config.option.backend == [conftest.ONPREM_BACKEND]


def test_pytest_configure_rejects_unsupported_backend() -> None:
    """Verify unsupported backend selections fail during pytest configuration."""
    conftest = _load_integration_conftest()
    config = SimpleNamespace(option=SimpleNamespace(backend=["cloud"]))

    with pytest.raises(pytest.UsageError):
        conftest.pytest_configure(config)


def test_backend_fixture_uses_single_onprem_backend() -> None:
    """Verify the project exposes a single backend fixture."""
    conftest = _load_integration_conftest()

    assert _fixture_function(conftest.backend)() == conftest.ONPREM_BACKEND


def _load_integration_conftest() -> Any:
    spec = importlib.util.spec_from_file_location(
        "integration_conftest",
        INTEGRATION_CONFTEST,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture_function(fixture: Any) -> Any:
    return fixture._fixture_function
