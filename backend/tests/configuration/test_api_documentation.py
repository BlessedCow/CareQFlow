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


def test_development_exposes_api_documentation(
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

    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_production_disables_api_documentation(
    monkeypatch,
):
    database_path = EXPECTED_DATABASE_DIRECTORY / "test_api_documentation.sqlcipher.db"

    database_path.unlink(missing_ok=True)
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

    try:
        with TestClient(
            create_app(),
            base_url="https://careqflow.local",
        ) as client:
            assert client.get("/docs").status_code == 404
            assert client.get("/redoc").status_code == 404
            assert client.get("/openapi.json").status_code == 404
    finally:
        database_path.unlink(missing_ok=True)


def test_development_can_enable_fastapi_debug(
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        "development",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_APP_DEBUG",
        "true",
    )

    api = create_app()

    assert api.debug is True
