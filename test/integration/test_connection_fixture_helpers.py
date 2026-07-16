"""Tests for integration connection fixture helpers."""

from __future__ import annotations

import test.integration.conftest as integration_conftest


def test_backend_certificate_fingerprint_prefers_dsn_value(
    monkeypatch,
) -> None:
    """Verify DSN-embedded fingerprints win over environment fallbacks."""
    monkeypatch.setenv("EXASOL_CERTIFICATE_FINGERPRINT", "ENVFINGERPRINT")

    fingerprint = integration_conftest._backend_certificate_fingerprint(
        {},
        dsn_fingerprint="DSNFINGERPRINT",
        host="db.example.com",
        port=8563,
        validate_certs=False,
    )

    assert fingerprint == "DSNFINGERPRINT"


def test_backend_certificate_fingerprint_falls_back_to_backend_params() -> None:
    """Verify backend parameters can provide a fingerprint outside the DSN."""
    fingerprint = integration_conftest._backend_certificate_fingerprint(
        {"certificate_fingerprint": "BACKENDFINGERPRINT"},
        dsn_fingerprint=None,
        host="db.example.com",
        port=8563,
        validate_certs=False,
    )

    assert fingerprint == "BACKENDFINGERPRINT"


def test_backend_certificate_fingerprint_falls_back_to_environment(
    monkeypatch,
) -> None:
    """Verify integration tests reuse the configured backend env fingerprint."""
    monkeypatch.setenv("EXASOL_CERTIFICATE_FINGERPRINT", "ENVFINGERPRINT")

    fingerprint = integration_conftest._backend_certificate_fingerprint(
        {},
        dsn_fingerprint=None,
        host="db.example.com",
        port=8563,
        validate_certs=False,
    )

    assert fingerprint == "ENVFINGERPRINT"


def test_backend_certificate_fingerprint_reads_live_endpoint_when_needed(
    monkeypatch,
) -> None:
    """Verify validate_certs=false can derive a live certificate fingerprint."""
    monkeypatch.delenv("EXASOL_CERTIFICATE_FINGERPRINT", raising=False)
    monkeypatch.setattr(
        integration_conftest,
        "_certificate_fingerprint_for_endpoint",
        lambda host, port: f"{host}:{port}:FINGERPRINT",
    )

    fingerprint = integration_conftest._backend_certificate_fingerprint(
        {},
        dsn_fingerprint=None,
        host="db.example.com",
        port=8563,
        validate_certs=False,
    )

    assert fingerprint == "db.example.com:8563:FINGERPRINT"
