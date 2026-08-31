from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.settings import EXPECTED_DATABASE_DIRECTORY, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def configure_production(
    monkeypatch,
    database_path,
):
    monkeypatch.setenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        "production",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "sqlcipher",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_SQLCIPHER_KEY",
        "a" * 32,
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_SESSION_COOKIE_SECURE",
        "true",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_CORS_ORIGINS",
        '["https://careqflow.local"]',
    )


def test_production_accepts_trusted_host(
    monkeypatch,
):
    database_path = (
        EXPECTED_DATABASE_DIRECTORY / "test_trusted_host_allowed.sqlcipher.db"
    )
    database_path.unlink(missing_ok=True)

    configure_production(
        monkeypatch,
        database_path,
    )

    try:
        with TestClient(
            create_app(),
            base_url="https://careqflow.local",
        ) as client:
            response = client.get("/api/health/live")

        assert response.status_code == 200
    finally:
        database_path.unlink(missing_ok=True)


def test_production_rejects_untrusted_host(
    monkeypatch,
):
    database_path = (
        EXPECTED_DATABASE_DIRECTORY / "test_trusted_host_rejected.sqlcipher.db"
    )
    database_path.unlink(missing_ok=True)

    configure_production(
        monkeypatch,
        database_path,
    )

    try:
        with TestClient(
            create_app(),
            base_url="https://evil.example",
        ) as client:
            response = client.get("/api/health/live")

        assert response.status_code == 400
        assert response.text == "Invalid host header"
    finally:
        database_path.unlink(missing_ok=True)


def test_development_does_not_apply_production_host_restriction(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        "development",
    )

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )

    with TestClient(
        create_app(),
        base_url="http://testserver",
    ) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
