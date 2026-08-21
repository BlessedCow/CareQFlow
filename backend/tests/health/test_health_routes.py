from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_health_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_endpoint_remains_available(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_endpoint_reports_running_application(client):
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_reports_available_database(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_generic_failure(client):
    with patch(
        "authstatus_api.main.get_conn",
        side_effect=RuntimeError("sensitive database details"),
    ):
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "sensitive database details" not in response.text
