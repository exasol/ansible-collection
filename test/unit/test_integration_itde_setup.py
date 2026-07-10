"""Static checks for the pytest integration ITDE setup."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_CONFTEST = PROJECT_ROOT / "test" / "integration" / "conftest.py"


def test_backend_option_and_fixture_are_not_defined() -> None:
    """Verify this project does not expose a backend matrix."""
    conftest = _load_integration_conftest()

    assert not hasattr(conftest, "pytest_configure")
    assert not hasattr(conftest, "backend")
    assert not hasattr(conftest, "ONPREM_BACKEND")


def test_external_itde_database_does_not_start_managed_database() -> None:
    """Verify external database mode does not create a managed ITDE environment."""
    conftest = _load_integration_conftest()
    itde_config = conftest.ItdeConfig(
        db_version=conftest.EXTERNAL_ITDE_VERSION,
    )
    exasol_config = conftest.OnpremDatabaseConfig(
        host="localhost",
        port=8563,
        username="sys",
        password="exasol",
    )

    database = _fixture_function(conftest.itde_database)(
        itde_config,
        exasol_config,
        "test-database",
    )

    assert next(database) is None
    with pytest.raises(StopIteration):
        next(database)


def test_exasol_database_params_use_exasol_config() -> None:
    """Verify pyexasol connection params come directly from Exasol config."""
    conftest = _load_integration_conftest()
    exasol_config = conftest.OnpremDatabaseConfig(
        host="db.example.test",
        port=8564,
        username="sys",
        password="secret",
    )

    params = _fixture_function(conftest.exasol_database_params)(None, exasol_config)

    assert params == {
        "dsn": "db.example.test:8564",
        "user": "sys",
        "password": "secret",
        "websocket_sslopt": {"cert_reqs": conftest.ssl.CERT_NONE},
    }


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
